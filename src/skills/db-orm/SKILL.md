---
name: db-orm
description: Use a general-purpose ORM for database access when the user asks for one or the project already has one - GORM for Go, SQLAlchemy 2 (async) for Python - behind the same port as the raw SQL adapter, so either works with PostgreSQL, MySQL, SQLite or SQL Server. The default stays raw SQL (go-code, py-code, rust-code), so do not reach for this skill otherwise. Covers when an ORM is right, the port and adapter layering, model rules and zero values, no N+1, bounded lists, upserts, transactions, the raw SQL escape hatch, tests that run on SQLite and PostgreSQL, and keeping the schema in goose migration files.
metadata:
  group: data
  summary: "GORM (Go) and SQLAlchemy 2 (Python) adapters behind the same port as raw SQL"
---

# Database ORM (opt-in: GORM for Go, SQLAlchemy 2 for Python)

**The default is raw SQL.** A service writes plain, readable SQL in a repository adapter (`go-code`, `py-code`,
`rust-code`: the `postgres` reference of each). Both styles sit behind **one repository port**, so the ORM adapter and the raw SQL
adapter are interchangeable, and each works with any database its driver supports. Use this skill **only** when:

- the user explicitly asks for an ORM ("use GORM", "use SQLAlchemy", "use the ORM"), or
- the project already has one (follow it; never put a second data layer into a service).

Otherwise stay on raw SQL. Never add an ORM "to save time" on a service that has none.

| Language | ORM | Databases | Reference | Tested adapter |
|---|---|---|---|---|
| Go | **GORM** v1.25 (`gorm.io/gorm`) | PostgreSQL, MySQL, SQLite, SQL Server | [go-gorm](references/go-gorm.md) | `assets/go-gorm/` |
| Python | **SQLAlchemy 2** async (`sqlalchemy.ext.asyncio`) | PostgreSQL, MySQL, SQLite, SQL Server, Oracle | [py-sqlalchemy](references/py-sqlalchemy.md) | `assets/python-sqlalchemy/` |
| Rust | none: raw SQL (`rust-code`); another ORM only if the project already uses one | | | |

## How to work

1. **Confirm the trigger** above. If neither applies, use the language skill's `postgres` reference.
2. **Discover the project**: the port, where models live, how transactions are opened, which database it runs. Follow it.
3. **Read** [orm-rules](references/orm-rules.md), then the language reference.
4. **Reuse the tested adapter** from `assets/`: same `items` table, same port as the raw adapter. Change `Item` for the domain type.
5. **Schema changes are goose files** (`db-migrations`), never `AutoMigrate` or `create_all` against a real database.
6. **Verify** on two databases: the adapter tests run on in-memory SQLite with no setup, and on PostgreSQL when `POSTGRES_*` is set.

## Which reference to read

| The request mentions | Read |
|---|---|
| when an ORM is right, layering, queries, transactions, escape hatch, other databases | [orm-rules](references/orm-rules.md) |
| Go, GORM, `gorm.DB`, `clause.OnConflict` | [go-gorm](references/go-gorm.md) |
| Python, SQLAlchemy, `AsyncSession`, `mapped_column` | [py-sqlalchemy](references/py-sqlalchemy.md) |
| migrations, schema change, DDL | the `db-migrations` skill |

## Rules that always apply

- **Raw SQL is the default**; the ORM is opt-in and lives **only inside the adapter**. Domain and application code never import it.
- **Same port, same table.** The ORM adapter implements the same repository port as the raw adapter and maps rows to domain types at the edge.
- **The schema is owned by goose files** (`db-migrations`). The ORM never creates or alters tables in a real database.
- **Zero values are values.** Models are plain (no pointers, no `omitempty`) over `NOT NULL DEFAULT` columns. GORM's struct `Updates` skips zero fields: update with a map.
- **No hidden queries**: one `IN` query per set, every list has a limit, one transaction per business operation and no Redis, Kafka or HTTP call inside it.
- **Keep raw SQL available** for queries the builder makes unreadable, in the readable multi-line layout.
- **Same environment contract**: `POSTGRES_*` (or the database's equivalent) from the config module, password from `NAME` or `NAME_FILE`, no default, never in a log or an error.
- **The driver decides the database**: one line (the GORM dialector, the SQLAlchemy URL) changes; the adapter code does not, except a dialect-specific upsert.

## Verify

```bash
# Go (assets/go-gorm): SQLite always, PostgreSQL when POSTGRES_* is set
golangci-lint run ./... && go test -race ./...
# Python (assets/python-sqlalchemy)
ruff check . && pytest -q
```

## Example prompts

- "use GORM for the orders repository" -> go-gorm, orm-rules · "use SQLAlchemy for the positions store" -> py-sqlalchemy
- "do I need an ORM here?" -> orm-rules (answer: no, raw SQL, unless asked)
- "make the store work on MySQL too" -> orm-rules (one dialector or URL, the dialect-specific upsert)
