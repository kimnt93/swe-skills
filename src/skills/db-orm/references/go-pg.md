# Go + go-pg v10 ORM

*Verified with: go-pg v10.15.0, Go 1.26, PostgreSQL 16; `assets/go-pg/store_test.go` and `zero_values_test.go` pass live with `-race`, `gofmt` and `go vet` are clean.*

Use it only when the ORM is requested or already in the project ([orm-rules](orm-rules.md)); the default is the same library
with raw SQL (`go-code/references/postgres.md`). go-pg v10 is the stack's one Go PostgreSQL library, so the ORM adapter adds no
dependency: it uses `pg.DB.Model(...)` instead of hand-written SQL.

Reference: `assets/go-pg/store.go` (adapter), `store_test.go` (live round trip) and `zero_values_test.go` (zero values are stored, not NULL).
Copy `store.go` next to the raw store, change `Item` for the domain type the project already has, and implement the same port.

## Setup

```bash
go get github.com/go-pg/pg/v10@v10.15.0
```

```go
db := pg.Connect(&pg.Options{
	Addr:     net.JoinHostPort(c.Host, strconv.Itoa(c.Port)),
	User:     c.User,
	Password: c.Password,
	Database: c.Database,
	PoolSize: c.PoolSize,
})
```

Settings come from the same `config.Postgres` the raw adapter uses (`POSTGRES_*`). Never log the options. `db.Ping(ctx)` is the
`postgres` check of `/healthz`.

## Model rules

```go
type itemModel struct {
	tableName struct{} `pg:"items,alias:i"`

	ID        string    `pg:"id,pk,type:uuid,use_zero"`
	Name      string    `pg:"name,use_zero"`
	CreatedAt time.Time `pg:"created_at,use_zero"`
}
```

- Plain value fields: **no pointers, no `omitempty`** anywhere.
- **`use_zero` on every written column.** Verified live: without it go-pg writes `""`, `0`, `false` and the zero time as `NULL`,
  which fails a `NOT NULL` column or silently changes meaning; with it they are stored and read back unchanged
  (`zero_values_test.go` proves it). Columns are `NOT NULL DEFAULT ...` so a field is never nil.
- Name every column in the tag; set `pk` and `type:uuid` on the ID; keep the model unexported and convert to the domain type (`toItem`).
- One model per table shape. A different projection is a different struct, or a raw query.

## Queries

```go
// One row; pg.ErrNoRows -> ErrNotFound.
err := db.ModelContext(ctx, &row).Where("i.id = ?", id).Select()

// A set in one query, newest first, bounded. pg.In renders the values for IN (?).
err := db.ModelContext(ctx, &rows).
	Where("i.id IN (?)", pg.In(ids)).
	Order("i.created_at DESC").
	Limit(500).
	Select()

// Idempotent write.
_, err := db.ModelContext(ctx, &row).
	OnConflict("(id) DO UPDATE").
	Set("name = EXCLUDED.name").
	Insert()

// One transaction per business operation.
err := db.RunInTransaction(ctx, func(tx *pg.Tx) error {
	_, err := tx.ModelContext(ctx, (*itemModel)(nil)).
		Set("name = ?", to).
		Where("name = ?", from).
		Update()

	return err
})
```

- Break a builder chain with one call per line (more than three calls).
- Raw SQL escape hatch: `db.WithContext(ctx).QueryOne(pg.Scan(&dest), query, args...)` with `query` a multi-line `const`, `?`
  placeholders, no casts in the select list. Queue claims (`FOR UPDATE SKIP LOCKED`) stay raw.
- Always the `...Context` forms with `ctx` first. Never concatenate user input into SQL (use `?`, and `pg.Ident` for
  code-chosen identifiers).

## Do not

- `orm.CreateTable` or `DropTable` against a real database; the schema is a goose file (`db-migrations`).
- Relations (`has-one`, `has-many`) and `.Relation(...)` loading inside a loop (N+1); load a set with one `IN` query or an explicit join.
- Return a go-pg model from a handler.
- Mix this adapter and a second data layer (pgx, bun, `database/sql`) in one service.
- Start a new service on go-pg's ORM because it is shorter: go-pg is in maintenance mode, so raw SQL stays the default.

## Checks

```bash
golangci-lint run ./...        # the go-code .golangci.yml: gofmt, lll 100, funlen, nestif, revive, errcheck
set -a; . ./.env; set +a; go test -tags integration -race ./...
```

## Example usage

- "Use the go-pg ORM for the orders repository, same port." · "Add a bounded `ListByIDs` with the ORM."
