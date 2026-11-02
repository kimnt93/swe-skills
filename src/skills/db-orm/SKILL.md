---
name: db-orm
description: Use an ORM for PostgreSQL access in Go (uptrace/bun), Python (SQLAlchemy 2 async) or Rust (SeaORM), only when the user asks for an ORM or the project already uses one. The default for every service is raw SQL (go-code, py-code, rust-code), so do not reach for this skill otherwise. Covers model rules, adapters behind the same ports as the raw SQL ones, transactions, no N+1, the raw SQL escape hatch, tested adapters, and keeping the schema in goose migration files.
metadata:
  group: data
---

# Database ORM (opt-in)

**The default is raw SQL.** Services in this stack write plain, readable SQL in a repository adapter (`go-code`, `py-code` and `rust-code`, their `postgres` reference). Use this skill **only** when:

- the user explicitly asks for an ORM ("use an ORM", "use SQLAlchemy / bun / SeaORM"), or
- the project already uses one (follow it; do not mix a second data layer into the same service).

Otherwise stay on raw SQL, and never add an ORM "to save time" on a service that has none.

## How to work

1. **Confirm the trigger** above. If neither applies, use the language skill's `postgres` reference instead.
2. **Discover the project**: the existing ORM and version, where models live, how sessions or transactions are opened. Follow it.
3. **Read** the reference for the language, plus [orm-rules](references/orm-rules.md) (the rules that hold for all three).
4. **Reuse the tested adapter** in `assets/`: same `items` table, same port as the raw SQL adapter, so one can replace the other.
5. **Schema changes are goose files**, never ORM auto-migration: read the `db-migrations` skill.
6. **Write readable code**: the layout rules of the language skill's `readable-code` reference apply to ORM chains and queries too.
7. **Verify** with the checks below and report what ran (live tests need PostgreSQL).

## Which reference to read

| The request mentions | Read |
|---|---|
| any ORM question, when an ORM is allowed, model rules, N+1, transactions, escape hatch | [orm-rules](references/orm-rules.md) |
| Go, bun, `uptrace/bun`, go-pg replacement | [go-bun](references/go-bun.md) (`assets/go-bun`) |
| Python, SQLAlchemy, async session, Alembic | [py-sqlalchemy](references/py-sqlalchemy.md) (`assets/python-sqlalchemy`) |
| Rust, SeaORM, entity, ActiveModel | [rust-sea-orm](references/rust-sea-orm.md) (`assets/rust-sea-orm`) |
| migrations, schema change, DDL | the `db-migrations` skill |

## Rules that always apply

- **Raw SQL is the default**; an ORM is opt-in and lives **only inside the adapter**. Domain and application code never import it.
- **Same port, same table.** The ORM adapter implements the same repository port as the raw adapter and maps rows to domain types at the edge.
- **The schema is owned by goose files** (`schemas/NNNN_name.sql`, `db-migrations`). No `AutoMigrate`, `create_all`, `Schema::create_table_from_entity` or `synchronize` against a real database.
- **No hidden queries**: no lazy loading (it breaks in async code and causes N+1), explicit eager loading or one `IN` query per set, every list has a `LIMIT`, one transaction per business operation and no Redis, Kafka or HTTP call inside it.
- **Keep raw SQL available** for queries the builder makes unreadable, written in the readable multi-line layout and without conversions in the select list.
- **Same environment contract**: `POSTGRES_*` from the config module, password from `NAME` or `NAME_FILE`, no default, never in a log or an error.
- Versions: bun 1.3, SQLAlchemy 2.1 with psycopg 3, SeaORM 2.0 (the assets were built against these on PostgreSQL 17); the project's lock file decides.

## Verify

```bash
# Go
golangci-lint run ./...
set -a; . ./.env; set +a; go test -tags integration -race ./...
# Python
uv run ruff format --check src tests && uv run ruff check src tests && uv run pytest -m integration -o addopts=""
# Rust
cargo clippy -p svc-infra --features orm --all-targets -- -D warnings
cargo test -p svc-infra --features orm --test orm_live -- --ignored
```

## Example prompts

- "use SQLAlchemy for the items repository" -> py-sqlalchemy, orm-rules · "swap go-pg for an ORM" -> go-bun
- "add SeaORM to this crate behind a feature" -> rust-sea-orm · "do I need an ORM here?" -> orm-rules (answer: no, raw SQL)
