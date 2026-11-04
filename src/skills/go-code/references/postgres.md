# Go + PostgreSQL (go-pg v10, raw SQL)

*Verified with: go-pg v10.15 and goose v3 on live PostgreSQL 17, including the zero-value and use_zero behaviour (scaffold e2e tests). go-pg is in maintenance mode; pgx v5 is the alternative where a repository already uses it.*

Write **raw SQL**, not query-builder chains. SQL is explicit, reviewable, copy-pasteable into `psql` and `EXPLAIN`, and
keeps performance in your hands. go-pg is used for connection pooling, parameter binding and struct scanning only.

Reference: `assets/template/internal/infrastructure/postgres/store.go` (rows, queries, transactions), `assets/template/internal/infrastructure/postgres/migrate.go`, `assets/template/internal/config/`
(env loader), `assets/env/postgres.env.example`. The same files are compiled and tested in the scaffold template.

## Environment (load from env, never hard-code)

```bash
# assets/env/postgres.env.example
POSTGRES_HOST=127.0.0.1   POSTGRES_PORT=5432   POSTGRES_DB=example   POSTGRES_USER=example
POSTGRES_PASSWORD=        # SECRET: required, no default, never committed; Swarm: POSTGRES_PASSWORD_FILE
POSTGRES_SSLMODE=disable  POSTGRES_POOL_SIZE=20
```

```go
l := config.NewLoader(nil)            // assets/template/internal/config/loader.go: os.Getenv, collects every problem
pgCfg := config.LoadPostgres(l)       // assets/template/internal/config/postgres.go
if err := l.Err(); err != nil { return err }   // lists each missing variable by name, never a value
store := postgres.Open(pgCfg)
```

Host, database, user and password are required; the port defaults to 5432; `sslmode=disable` is for local use only.

## Row structs: the house rules

```go
// itemRow maps the columns of `items`.
type itemRow struct {
    ID        string    `pg:"id,use_zero"`
    Name      string    `pg:"name,use_zero"`
    CreatedAt time.Time `pg:"created_at,use_zero"`
    Label     string    `pg:"-"` // ignored: not a column, filled in Go
}
```

1. **One plain struct per query shape**, fields mapped with `pg:"column"`. Name tags explicitly; never rely on the
   default snake-casing of field names.
2. **Ignored fields use `pg:"-"`** (computed values, helpers, joined labels). go-pg never reads or writes them.
3. **No pointers.** Fields are values (`string`, `int64`, `bool`, `time.Time`), never `*string`/`sql.NullString`. Make columns
   `NOT NULL DEFAULT ...` so a field is its zero value, never nil. For a nullable legacy column, read it with
   `COALESCE(col, '')` in the SELECT (the one allowed expression) instead of a pointer.
4. **No `omitempty`**, on `pg` or `json` tags. A zero value is a value: it is written and serialised, not dropped.
5. **Tag every written column `use_zero`.** Verified against live PostgreSQL: without it go-pg writes Go zero values
   (`""`, `0`, `false`, zero time) as **NULL** (2 of 2 test columns became NULL), which breaks `NOT NULL` columns or silently
   changes meaning. With `use_zero` they are stored as real values and read back unchanged.
6. **Rows are not domain types.** Convert at the edge (`row.toDomain()`); domain code never sees a `pg` tag.

## Queries

```go
// One query per constant, written the way psql would run it: one clause per line, one column per line.
const (
    sqlInsertItem = `
INSERT INTO items (id, name, created_at)
VALUES (?id, ?name, ?created_at)
`

    sqlGetItem = `
SELECT
    id,
    name,
    created_at
FROM items
WHERE id = ?
`

    sqlListItems = `
SELECT
    id,
    name,
    created_at
FROM items
WHERE id IN (?)
ORDER BY created_at DESC
LIMIT 500
`
)

db.ExecContext(ctx, sqlInsertItem, &row)                 // ?id ?name ?created_at read the struct fields
db.QueryOneContext(ctx, &row, sqlGetItem, id)            // one row; pg.ErrNoRows when absent
db.QueryContext(ctx, &rows, sqlListItems, pg.In(ids))    // many rows, one query (no N+1)
db.QueryOneContext(ctx, pg.Scan(&n), `SELECT count(*) FROM items`)   // a scalar
```

- SQL is a named `const` next to the method that runs it. Placeholders are `?` (positional) or `?field` (struct field).
  **Never concatenate user input**; for a code-chosen identifier use `pg.Ident`, for a code-chosen fragment `pg.Safe`.
- Select the columns the struct needs, **as they are**: no `::text`, `::float8`, `CAST` or `to_char` in the select list. The `pg`-tagged struct does the
  conversion (go-pg scans `uuid` into `string` and `timestamptz` into `time.Time`, verified live). `SELECT *` is not allowed in code. Layout rules: [readable-code](readable-code.md).
- Always the context variants (`ExecContext`, `QueryContext`, `QueryOneContext`); `ctx` is the first parameter.
- **Bound every list** (`LIMIT`), index filter columns in the migration, no N+1.
- **Idempotent writes:** `INSERT ... ON CONFLICT (id) DO UPDATE SET ...` so replays converge.
- **Work queues:** `SELECT ... ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED` inside a transaction (`ClaimOldest`).
- **Transactions:** `db.RunInTransaction(ctx, func(tx *pg.Tx) error {...})`: one per business operation, rollback on error,
  no other repository, Redis, Kafka or HTTP call inside. Keep one global lock order when locking several rows.
- **Errors:** `errors.Is(err, pg.ErrNoRows)` -> the application sentinel (`application.ErrNotFound`); wrap the rest
  (`fmt.Errorf("list items by id: %w", err)`); never return driver text to a client.
- **Money/exact numbers:** `numeric` in SQL; convert to a decimal or scaled integer at the edge; never compare floats with `==`.
- **Timestamps:** `timestamptz`, UTC in and out (`row.CreatedAt.UTC()`).

## Pool, TLS, health

`pg.Options{PoolSize, DialTimeout, ReadTimeout}`; any `sslmode` other than `disable` sets
`tls.Config{ServerName: host, MinVersion: tls.VersionTLS12}`. `db.Ping(ctx)` is the `postgres` check of `/healthz` (api-contract skill). Never log the DSN
or password.

## Migrations (goose)

- Files `schemas/NNNN_name.sql` with `-- +goose Up` and a working `-- +goose Down`; **never edit a released file**, add a
  version. Columns `NOT NULL DEFAULT ...` (see `0002_zero_values.sql`).
- `postgres.Migrate(ctx, cfg, "schemas")` (goose through `database/sql` with pgx's stdlib driver, migrations only) runs from
  `cmd/api migrate` as a one-shot job before the service rolls out (`deployment-setup`: `migration_compose_file`).
- A schema change = migration + row struct + SQL constant + port change + test, in one change. Safe patterns (concurrent indexes, backfills,
  expand and contract) and the migration linter: the `db-migrations` skill. Prefer an ORM? Only when asked: the `db-orm` skill (go-pg v10's ORM, same library).

## Tracing

go-pg has no maintained OTel hook: wrap repository methods with `PeerSpan(ctx, "postgres", "select orders")` from
`service-tracing`. Never put SQL text or arguments in spans.

## Checks

```bash
golangci-lint run ./... && go test -race ./...
docker compose -f docker-compose.infra.local.yaml up -d postgres && scripts/health.sh --wait postgres
set -a; . ./.env; set +a; go test -tags integration -race ./internal/e2e/...   # migrate, round trip, zero values, upsert, SKIP LOCKED
```

## Example usage

- “Add a repository method that lists open orders by symbol: raw SQL, bounded, with an index.”
- “Write the migration and the row struct for a new `positions` table (no pointers, use_zero).”
