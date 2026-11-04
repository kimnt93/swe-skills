# ORM rules (Go + go-pg v10)

*Built and tested live: go-pg v10.15 (Go 1.26), against PostgreSQL 16.*

## When an ORM is acceptable

| Situation | Choice |
|---|---|
| A new service, nobody asked for an ORM | **Raw SQL** (`go-code`) |
| The user asks for the ORM, or the repository already uses it | This skill |
| Reports, bulk loads, hot paths, window functions, `COPY`, `SKIP LOCKED` queues | Raw SQL, even inside an ORM project (the escape hatch) |
| Two data layers in one service | Never; pick the project's one |

## Layering

```text
application (use cases)  ->  port (repository interface)  ->  adapter (ORM here only)
```

- The adapter is the only file set that imports `pg.DB.Model`. A model type is **not** a domain type: convert at the edge
  (`toItem`), so the API and the domain never see ORM types or tags.
- The ORM adapter and the raw SQL adapter satisfy the same port. Tests of the use cases use fakes, not the ORM.

## Models

- Plain value fields, no pointers, no `omitempty`, `use_zero` on every written column (verified: without it a zero `string`, `int64`,
  `bool` or `time.Time` is written as NULL). Columns are `NOT NULL DEFAULT ...` so a field is never nil by accident.
- Name every column explicitly in the tag; never rely on automatic name conversion.
- Timestamps are `timestamptz`, UTC in and out. Exact numbers are `numeric` mapped to a decimal type, never a float, for money.
- IDs: `uuid` column; keep the domain ID a `string`.

## Queries

1. **One query per set** (`pg.In` list, join, or explicit loading). Never load children inside a loop.
2. **Bound every list** (`Limit`), index the filter columns in a migration.
3. **Select only what the model needs**; no `SELECT *` in raw fragments, no conversions in the select list (`::text`, `CAST`).
4. **Idempotent writes** use `OnConflict(...)`, queue claims use raw `FOR UPDATE SKIP LOCKED`.
5. **Transactions**: one per business operation (`RunInTransaction`), rolled back on error, no other I/O inside.
6. **Errors**: map `pg.ErrNoRows` to the application's `NotFound`; wrap the rest; never return driver or SQL text to a client.
7. **The escape hatch** (`QueryOne`, `Query` with a raw `const`) is for queries the builder makes harder to read than SQL.

## Schema and migrations

The ORM never creates or alters the schema. Tables change through goose files (`db-migrations`); the model is updated in the same
change as the migration.

## Testing

- Use-case tests: fakes behind the port.
- Adapter tests: a real PostgreSQL (`-tags integration`), applying the goose `Up` files first. Cover create, get, missing row,
  upsert twice, a list by ids, a zero-value round trip, and a transaction rollback.

## Related

[go-pg](go-pg.md) · `db-migrations` · `go-code`'s `postgres` and `readable-code` references.
