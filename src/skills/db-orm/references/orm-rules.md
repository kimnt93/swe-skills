# ORM rules (GORM for Go, SQLAlchemy 2 for Python)

*Built and tested live: GORM v1.25.12 (Go 1.26) and SQLAlchemy 2.0 (Python 3.12), each on in-memory SQLite and on PostgreSQL 16.*

## When an ORM is acceptable

| Situation | Choice |
|---|---|
| A new service, nobody asked for an ORM | **Raw SQL** (`go-code`, `py-code`, `rust-code`) |
| The user asks for an ORM, or the repository already uses one | This skill: GORM (Go), SQLAlchemy (Python) |
| Reports, bulk loads, hot paths, window functions, `COPY`, `SKIP LOCKED` queues | Raw SQL, even inside an ORM project (the escape hatch) |
| Two data layers in one service | Never; pick the project's one |

## Layering: one port, two interchangeable adapters

```text
application (use cases)  ->  port (repository interface)  ->  adapter: raw SQL  |  adapter: ORM
```

- The ORM is imported only by the adapter files. A model type is **not** a domain type: convert at the edge (`toItem`, `_item`), so
  the API and the domain never see ORM types, tags or sessions.
- The raw SQL adapter and the ORM adapter satisfy the same port and use the same table. Use-case tests use fakes, not the ORM.
- **Any database**: the port does not name one. A new database means a new connection line (GORM dialector, SQLAlchemy URL), the
  goose migrations for it, and a review of the places SQL differs (below). Raw SQL adapters have the same limit: placeholders
  differ (`$1`, `?`, `:name`), and so do upsert, `RETURNING`, JSON and array types. Keep those in one small method each.

## Models

- Plain value fields; every column `NOT NULL` with a default where it makes sense, so a field is never nil by accident.
- Name every column in the tag or `mapped_column`; never rely on naming conventions. Pin the table name.
- Timestamps are UTC in and out (`timestamptz` on PostgreSQL). Exact numbers (money) are `numeric` mapped to a decimal type, never a float.
- IDs: a `uuid` column; the domain id stays a string (`Uuid(as_uuid=False)` in SQLAlchemy).
- **GORM zero values:** `Create(&struct)` writes every field, zero values included; `Updates(struct)` **skips** zero fields, so update with
  `map[string]any` (or `Select(...)`). `assets/go-gorm/zero_values_test.go` proves both.

## Queries

1. **One query per set** (`IN`, join, `Preload`/`selectinload`). Never load children inside a loop.
2. **Bound every list** (`Limit`, `.limit()`), index the filter columns in a migration.
3. **Select only what the model needs**; no `SELECT *` in raw fragments.
4. **Idempotent writes** use the upsert of the driver: `clause.OnConflict` (GORM, all databases), `on_conflict_do_update` (SQLAlchemy,
   PostgreSQL and SQLite; MySQL uses `on_duplicate_key_update`). Queue claims use raw `FOR UPDATE SKIP LOCKED`.
5. **Transactions**: one per business operation (`db.Transaction`, `session.begin()`), rolled back on error, no other I/O inside.
6. **Errors**: map `gorm.ErrRecordNotFound` / a missing `session.get` to the application's `NotFound`; wrap the rest; never return
   driver or SQL text to a client.
7. **The escape hatch** (`db.Raw(...)`, `text(...)`) is for queries the builder makes harder to read than SQL, written as a multi-line `const`.
8. **No lazy loading in async code** (SQLAlchemy): `expire_on_commit=False`, load what you need up front.

## Schema and migrations

The ORM never creates or alters the schema (`AutoMigrate`, `metadata.create_all`). Tables change through goose files (`db-migrations`);
the model is updated in the same change as the migration. Test helpers may create a portable table on SQLite only.

## Testing

- Use-case tests: fakes behind the port.
- Adapter tests run on **two databases with the same code**: in-memory SQLite by default (no setup), and PostgreSQL when `POSTGRES_HOST`
  is set (apply the goose `Up` files first). Cover create, get, missing row, upsert twice, a list by ids, a zero-value round trip, and a
  transaction rollback.

## Related

[go-gorm](go-gorm.md) · [py-sqlalchemy](py-sqlalchemy.md) · `db-migrations` · the `postgres` and `readable-code` references of `go-code` and `py-code`.
