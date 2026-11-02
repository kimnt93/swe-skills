# Go + uptrace/bun

*Verified with: bun 1.3.0 (`pgdialect`, `pgdriver`), Go 1.27, PostgreSQL 17; `assets/go-bun/store_test.go` and `zero_values_test.go` pass live and `golangci-lint` (with the go-code config) reports 0 issues.*

Use it only when an ORM is requested or already in the project ([orm-rules](orm-rules.md)); the default is go-pg with raw SQL
(`go-code/references/postgres.md`). bun is the maintained successor to go-pg, so migrating from go-pg to an ORM usually means bun.

Reference: `assets/go-bun/store.go` (adapter), `store_test.go` (live round trip) and `zero_values_test.go` (zero values are stored, not NULL). Copy `store.go` next to the raw store, change
`Item` for the domain type the project already has, and implement the same port.

## Setup

```bash
go get github.com/uptrace/bun github.com/uptrace/bun/dialect/pgdialect github.com/uptrace/bun/driver/pgdriver
```

```go
dsn := url.URL{
	Scheme:   "postgres",
	User:     url.UserPassword(c.User, c.Password),
	Host:     net.JoinHostPort(c.Host, strconv.Itoa(c.Port)),
	Path:     c.Database,
	RawQuery: "sslmode=" + c.SSLMode,
}

sqldb := sql.OpenDB(pgdriver.NewConnector(pgdriver.WithDSN(dsn.String())))
db := bun.NewDB(sqldb, pgdialect.New())
```

Settings come from the same `config.Postgres` the raw adapter uses (`POSTGRES_*`). The DSN contains the password: never log it. Ping
with `db.PingContext(ctx)` as the `postgres` check of `/healthz`.

## Model rules

```go
type itemModel struct {
	bun.BaseModel `bun:"table:items,alias:i"`

	ID        string    `bun:"id,pk,type:uuid"`
	Name      string    `bun:"name,notnull"`
	CreatedAt time.Time `bun:"created_at,notnull"`
}
```

- Plain value fields: **no pointers, no `nullzero`, no `omitempty`** anywhere. Verified: a zero `string`, `int64`, `bool` and
  `time.Time` is stored as a real value in a `NOT NULL DEFAULT` column and read back unchanged (no `use_zero` equivalent is needed;
  `zero_values_test.go` proves it).
- Tag every column name; set `pk` and `type:uuid` on the ID; keep the model unexported and convert to the domain type (`toItem`).
- One model per table shape. A different projection is a different struct, or a raw query.

## Queries

```go
// One row; sql.ErrNoRows -> ErrNotFound.
err := db.NewSelect().Model(&row).Where("i.id = ?", id).Scan(ctx)

// A set in one query, newest first, bounded. bun.List renders the values for IN (?).
err := db.NewSelect().
	Model(&rows).
	Where("i.id IN (?)", bun.List(ids)).
	OrderExpr("i.created_at DESC").
	Limit(500).
	Scan(ctx)

// Idempotent write.
_, err := db.NewInsert().
	Model(&row).
	On("CONFLICT (id) DO UPDATE").
	Set("name = EXCLUDED.name").
	Exec(ctx)

// One transaction per business operation.
err := db.RunInTx(ctx, nil, func(ctx context.Context, tx bun.Tx) error {
	_, err := tx.NewUpdate().
		Model((*itemModel)(nil)).
		Set("name = ?", to).
		Where("name = ?", from).
		Exec(ctx)

	return err
})
```

- Break a builder chain with one call per line (more than three calls). `bun.In` is deprecated: use `bun.List` (verified) or `bun.Tuple`.
- Raw SQL escape hatch: `db.NewRaw(query, args...).Scan(ctx, &dest)` with `query` a multi-line `const`, `?` placeholders, no casts in the
  select list. Queue claims (`FOR UPDATE SKIP LOCKED`) stay raw.
- Always the `...Context` forms with `ctx` first. Never concatenate user input into SQL (use `?` and `bun.Ident` for code-chosen identifiers).

## Do not

- `db.NewCreateTable()`, `ResetModel`, `bun.migrate` against a real database; the schema is a goose file (`db-migrations`). If the project
  already uses `bun/migrate`, keep that one system.
- Relations with `rel:` and `.Relation(...)` loading inside a loop (N+1); load a set with one `IN` query or an explicit join.
- Return a `bun` model from a handler.

## Checks

```bash
golangci-lint run ./...        # the go-code .golangci.yml: gofmt, lll 100, funlen, nestif, revive, errcheck
set -a; . ./.env; set +a; go test -tags integration -race ./...
```

## Example usage

- "Replace the go-pg store with bun, same port." · "Add a bun repository for orders with a bounded query."
