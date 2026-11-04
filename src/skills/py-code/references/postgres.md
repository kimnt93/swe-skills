# Python + PostgreSQL (psycopg 3)

*Verified with: psycopg 3.3 and PostgreSQL 17 in the scaffold template (unit and live integration tests, ruff and pycodestyle clean).*

Plain SQL by default: explicit, reviewable, `EXPLAIN`-able. Reference: `assets/template/src/service/db/postgres.py` (repository),
`assets/template/src/service/settings/` (environment loading), `assets/env/postgres.env.example`. The same files are tested in the scaffold template.
Code follows PEP 8 (79 columns; `ruff` with `E W F I N`, checked by `pycodestyle`).

## Environment (load from env)

```bash
# assets/env/postgres.env.example
POSTGRES_HOST=127.0.0.1  POSTGRES_PORT=5432  POSTGRES_DB=example  POSTGRES_USER=example
POSTGRES_PASSWORD=       # SECRET: required, no default, never committed; Swarm: POSTGRES_PASSWORD_FILE
POSTGRES_SSLMODE=disable POSTGRES_POOL_SIZE=10
```

```python
from service.settings import PostgresSettings      # assets/template/src/service/settings/postgres.py (+ _base.py)

settings = PostgresSettings()          # raises ValidationError naming each missing variable, never a value
repo = await PostgresItems.open(settings)
```

`postgres_password` is a `SecretStr` with no default: `repr`, `model_dump` and logs never show it, and a missing one fails by
name. `conninfo` contains the password: never log it.

## Rules

1. **SQL lives only in the adapter**, as module-level triple-quoted constants (one query each, one clause and one column per line) with `%s`
   placeholders and a parameter tuple; **never** f-strings or `%` formatting with user input. A code-chosen identifier uses
   `psycopg.sql.Identifier`. **No conversions in the select list** (`id::text`, `value::float8`, `CAST`; a *parameter* cast such as `%s::uuid[]` is fine): select the raw column and convert
   in the row mapping (`str(row["id"])`, `Decimal`). Layout rules and bad/good examples: [readable-code](readable-code.md).
2. **Async pool:** `AsyncConnectionPool(conninfo, min_size, max_size, open=False, kwargs={"row_factory": dict_row})`, opened in the
   lifespan (`await pool.open(wait=True)`), closed on shutdown. `async with pool.connection() as conn:` per operation.
3. **One transaction per business operation:** the connection context commits on success and rolls back on error; use
   `async with conn.transaction():` for explicit scopes. No Redis/Kafka/HTTP call inside it.
4. **Rows are not domain types.** Map `dict_row` results to frozen `@dataclass(slots=True)` values at the edge (`_to_item(row)`); the domain never
   imports psycopg. Timestamps are `timestamptz`, aware UTC datetimes in and out.
5. **No N+1, always bounded:** load sets with `WHERE id = ANY(%s::uuid[])`, `LIMIT` on every list, index filter columns in the
   migration, batch with `executemany` or `COPY` (`cursor.copy`) for bulk.
6. **Idempotent writes:** `INSERT ... ON CONFLICT (id) DO UPDATE SET ...`. **Work queues:** `... ORDER BY created_at LIMIT 1 FOR UPDATE
   SKIP LOCKED` inside a transaction so replicas never block each other.
7. **Errors:** a missing row raises the domain `NotFoundError` (a typed exception ending in `Error`, PEP 8); a unique violation maps from
   `psycopg.errors.UniqueViolation`; never return driver text to a client.
8. **Exact numbers:** `numeric` in SQL and `decimal.Decimal` (or scaled integers) in Python; never floats for money.
9. **Health:** `await conn.execute("SELECT 1")` is the `postgres` check of `/healthz`.
10. **Blocking code stays out of `async def`:** use the async pool (not `psycopg.connect`) in async services; sync scripts may use
    `psycopg_pool.ConnectionPool`.

## Migrations (goose)

SQL files `schemas/NNNN_name.sql` with `-- +goose Up` and a working `-- +goose Down`, applied by the goose binary as a one-shot
job before the service rolls out (`deployment-setup`: `migration_compose_file`). **Never edit a released file**; add a version. Safe patterns (concurrent indexes, backfills, expand and contract) and the migration
linter: the `db-migrations` skill. Python services use plain SQL; with an ORM requested or already present, SQLAlchemy 2 (`db-orm`).
Columns are `NOT NULL DEFAULT ...` where a default exists, so Python values are never `None` by accident.

## Checks

```bash
uv run ruff format --check src tests && uv run ruff check src tests && uv run pytest
docker compose -f docker-compose.infra.local.yaml up -d postgres && scripts/health.sh --wait postgres
set -a; . ./.env; set +a; uv run pytest -m integration -o addopts=""    # round trip, upsert, SKIP LOCKED
```

## Example usage

- “Add a repository method that lists open orders by symbol: SQL, bounded, indexed.”
- “Write the migration and the dataclass row for a new `positions` table.”
