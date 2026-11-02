# Rust + PostgreSQL (tokio-postgres, raw SQL)

Adapter: `assets/template/crates/svc-infra/src/postgres.rs`; settings: `assets/template/crates/svc-core/src/config/postgres.rs`; env: `assets/env/postgres.env.example`; load it as described in [env-config](env-config.md). Tested live in the scaffold.

Raw SQL with `$1` parameters in the infra crate only, as `const` strings written multi-line (one clause and one column per line; layout rules and
bad/good examples in [readable-code](readable-code.md)); **no conversions in the select list** (`id::text`, `value::float8`, `CAST`): select the raw
column and convert in Rust (`row.get::<_, Uuid>(0)`, a `From` impl); `deadpool_postgres::Pool` with `RecyclingMethod::Fast`; rows map to domain types at the
edge (`time::OffsetDateTime` via `with-time-0_3`, UTC); `query_opt` -> `Error::NotFound`; `ON CONFLICT ... DO UPDATE` for idempotent writes;
one transaction per business operation (`client.transaction()`); never return driver text (`Error::Storage("database operation failed")`,
log the cause where handled). TLS: swap `NoTls` for `tokio-postgres-rustls` outside local development. `ping()` is the `postgres` check of `/healthz`.

Schema changes are goose SQL files (`schemas/NNNN_name.sql`, applied by a one-shot job): safe patterns and the migration linter are in the
`db-migrations` skill. Prefer an ORM? Only when asked: the `db-orm` skill (SeaORM, behind an `orm` feature).

## Example usage

- “Add a repository method that lists open orders by symbol, bounded, with an index.”
- “Load Postgres settings from the environment with the password from a file.”
