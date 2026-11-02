# ORM rules (all languages)

*Built and tested live: uptrace/bun 1.3 (Go 1.27), SQLAlchemy 2.1 + psycopg 3.3 (Python 3.12), SeaORM 2.0.4 (Rust 1.99), against PostgreSQL 17.*

## When an ORM is acceptable

| Situation | Choice |
|---|---|
| A new service, nobody asked for an ORM | **Raw SQL** (`go-code`, `py-code`, `rust-code`) |
| The user asks for an ORM, or the repository already uses one | This skill |
| Reports, bulk loads, hot paths, window functions, `COPY`, `SKIP LOCKED` queues | Raw SQL, even inside an ORM project (the escape hatch) |
| Two data layers in one service | Never; pick the project's one |

## Layering

```text
application (use cases)  ->  port (repository trait/Protocol/interface)  ->  adapter (ORM here only)
```

- The adapter is the only file set that imports the ORM. A model/entity/row type is **not** a domain type: convert at the edge
  (`toItem`/`_to_item`/`to_item`), so the API and the domain never see ORM types, tags or sessions.
- The ORM adapter and the raw SQL adapter satisfy the same port. Tests of the use cases use fakes, not the ORM.

## Models

- Plain value fields. Go: no pointers, no `nullzero`, no `omitempty` (verified: bun then writes `''`, `0`, `false` and the zero time as
  real values). Columns are `NOT NULL DEFAULT ...` where a default exists, so a field is never nil by accident.
- Name every column explicitly in the mapping; never rely on automatic name conversion.
- Timestamps are `timestamptz`, UTC in and out. Exact numbers are `numeric` mapped to a decimal type, never a float, for money.
- IDs: `uuid` column; keep the Go/Python domain ID a `string`, convert in the model (`Uuid(as_uuid=False)`, `type:uuid`).

## Queries

1. **One query per set** (`IN`/`ANY` list, join, or explicit eager loading). Never load children inside a loop.
2. **Bound every list** (`LIMIT`), index the filter columns in a migration.
3. **Select only what the model needs**; no `SELECT *` in raw fragments, no conversions in the select list (`::text`, `CAST`):
   the model converts.
4. **Idempotent writes** use the ORM's `ON CONFLICT` support, queue claims use raw `FOR UPDATE SKIP LOCKED`.
5. **Transactions**: one per business operation (`RunInTx`, `session.begin()`, `DatabaseTransaction`), rolled back on error, no other
   I/O inside.
6. **Errors**: map "no rows" to the application's `NotFound`; wrap the rest; never return driver or SQL text to a client.
7. **The escape hatch** (`NewRaw`, `text()`, `Statement::from_sql_and_values`) is for queries the builder makes harder to read than SQL.
   Write it as a named constant in the multi-line layout (see the language's `readable-code`).

## Schema and migrations

The ORM never creates or alters the schema. Tables change through goose files (`db-migrations`); the model is updated in the same
change as the migration. If the project already uses the ORM's own migration tool (Alembic, `sea-orm-migration`, bun migrations), keep
it and do not run two migration systems against one database; `db-migrations` lists how.

## Testing

- Use-case tests: fakes behind the port.
- Adapter tests: a real PostgreSQL (`-tags integration`, `pytest -m integration`, `#[ignore]`), applying the goose `Up` files first.
  Cover create, get, missing row, upsert twice, a list by ids, and a transaction rollback.

## Related

[go-bun](go-bun.md) · [py-sqlalchemy](py-sqlalchemy.md) · [rust-sea-orm](rust-sea-orm.md) · `db-migrations` · the language skills' `postgres`
and `readable-code` references.
