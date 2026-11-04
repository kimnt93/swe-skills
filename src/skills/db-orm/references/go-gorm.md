# Go + GORM

*Verified with: gorm.io/gorm v1.25.12, gorm.io/driver/postgres v1.5.11, github.com/glebarez/sqlite (tests), Go 1.26. `assets/go-gorm` passes with `-race` on in-memory SQLite and on PostgreSQL 16; `gofmt` and `go vet` are clean.*

Use it only when an ORM is requested or already in the project ([orm-rules](orm-rules.md)); the default is raw SQL
(`go-code/references/postgres.md`).

Reference: `assets/go-gorm/store.go` (adapter), `open_test.go` (SQLite or PostgreSQL by environment), `store_test.go` (round trip,
upsert twice, rollback), `zero_values_test.go` (zero values). Copy `store.go` next to the raw store, change `Item` for the project's
domain type, implement the same port.

## Setup

```bash
go get gorm.io/gorm@v1.25.12 gorm.io/driver/postgres@v1.5.11
```

```go
db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})   // gorm.io/driver/postgres
store := ormstore.New(db)
```

Build the DSN from the `POSTGRES_*` settings the raw adapter uses; never log it. Another database changes only the dialector:
`mysql.Open`, `sqlite.Open`, `sqlserver.Open`. `Ping` is the database check of `/healthz`. Set the pool on `db.DB()`
(`SetMaxOpenConns`, `SetConnMaxLifetime`).

## Model

```go
type itemModel struct {
	ID        string    `gorm:"column:id;primaryKey"`
	Name      string    `gorm:"column:name"`
	CreatedAt time.Time `gorm:"column:created_at"`
}

func (itemModel) TableName() string { return "items" }
```

No pointers, no `omitempty`, every column named. `CreatedAt` here is an ordinary column the application sets: GORM would also fill a
field called `CreatedAt` automatically if it were zero, so pass the time explicitly in the domain.

## Operations

| Need | GORM |
|---|---|
| insert (zero values written) | `db.Create(&row)` |
| one row, missing is an error | `db.Where("id = ?", id).Take(&row)`; `errors.Is(err, gorm.ErrRecordNotFound)` -> `ErrNotFound` |
| a set, one query | `db.Where("id IN ?", ids).Order(...).Limit(500).Find(&rows)` |
| idempotent upsert | `Clauses(clause.OnConflict{Columns: ..., DoUpdates: clause.AssignmentColumns([]string{"name"})}).Create(&row)` |
| update, zero values included | `db.Model(&itemModel{}).Where(...).Updates(map[string]any{"qty": 0})` |
| transaction | `db.Transaction(func(tx *gorm.DB) error { ... })` (error rolls back) |
| raw SQL | `db.Raw(query, args...).Scan(&dest)` with a multi-line `const` |

## Pitfalls

- **Struct `Updates` skips zero values** (`0`, `""`, `false`): use a map or `Select("qty", "active")`. A struct `Save` writes all fields.
- **`Delete`/`Update` without `Where`** is refused by GORM (`ErrMissingWhereClause`); never bypass it with `AllowGlobalUpdate`.
- **`AutoMigrate`** is for tests on SQLite only; a real database gets goose files.
- **`Preload` or a join** for children; never query inside a loop. Use `db.Debug()` locally to see the SQL, never in production.
- **Context**: always `db.WithContext(ctx)` so cancellation and deadlines reach the driver.
- **Logger**: GORM logs SQL and parameters at `Info`; keep the default `Warn` or `Silent` so values never reach logs.
