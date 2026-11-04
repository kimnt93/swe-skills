---
name: db-orm
description: Use the go-pg v10 ORM (pg.DB.Model) for PostgreSQL access in Go services, only when the user asks for an ORM or the project already uses it. The default is raw SQL on the same library (go-code postgres reference), so do not reach for this skill otherwise. Covers model rules (use_zero, no pointers), an adapter behind the same port as the raw SQL one, bounded queries, upserts, transactions, no N+1, the raw SQL escape hatch, a live-tested adapter, and keeping the schema in goose migration files.
metadata:
  group: data
  summary: "Opt-in go-pg v10 ORM adapter behind the same port as raw SQL"
---

# Database ORM (opt-in, Go + go-pg v10)

**The default is raw SQL.** Go services write plain, readable SQL in a repository adapter (`go-code`, its `postgres` reference) on go-pg v10. Use this skill **only** when:

- the user explicitly asks for an ORM ("use the ORM", "use `Model(...)`"), or
- the project already uses go-pg's ORM (follow it; do not mix a second data layer into the same service).

Otherwise stay on raw SQL, and never add the ORM "to save time" on a service that has none. One library, go-pg v10, is enough:
no bun, no GORM, no ORM for Python or Rust (those use raw SQL: `py-code`, `rust-code`).

## How to work

1. **Confirm the trigger** above. If neither applies, use `go-code`'s `postgres` reference instead.
2. **Discover the project**: where models live, how transactions are opened. Follow it.
3. **Read** [go-pg](references/go-pg.md) and [orm-rules](references/orm-rules.md).
4. **Reuse the tested adapter** in `assets/go-pg/`: same `items` table, same port as the raw SQL adapter, so one can replace the other.
5. **Schema changes are goose files**, never `orm.CreateTable`: read the `db-migrations` skill.
6. **Write readable code**: the `readable-code` reference of `go-code` applies to ORM chains and queries too.
7. **Verify** with the checks below and report what ran (the live tests need PostgreSQL).

## Which reference to read

| The request mentions | Read |
|---|---|
| when an ORM is allowed, model rules, N+1, transactions, escape hatch | [orm-rules](references/orm-rules.md) |
| Go, go-pg, `pg.DB.Model`, `use_zero` | [go-pg](references/go-pg.md) (`assets/go-pg`) |
| migrations, schema change, DDL | the `db-migrations` skill |

## Rules that always apply

- **Raw SQL is the default**; the ORM is opt-in and lives **only inside the adapter**. Domain and application code never import it.
- **Same port, same table.** The ORM adapter implements the same repository port as the raw adapter and maps rows to domain types at the edge.
- **The schema is owned by goose files** (`schemas/NNNN_name.sql`, `db-migrations`). No `orm.CreateTable` against a real database.
- **`use_zero` on every written column, no pointers, no `omitempty`.**
- **No hidden queries**: one `IN` query per set, every list has a `LIMIT`, one transaction per business operation and no Redis, Kafka or HTTP call inside it.
- **Keep raw SQL available** for queries the builder makes unreadable, written in the readable multi-line layout.
- **Same environment contract**: `POSTGRES_*` from the config module, password from `NAME` or `NAME_FILE`, no default, never in a log or an error.
- Version: go-pg v10.15 (the assets were built against it on PostgreSQL 16); the project's `go.mod` decides.

## Verify

```bash
golangci-lint run ./...
set -a; . ./.env; set +a; go test -tags integration -race ./...
```

## Example prompts

- "use the go-pg ORM for the items repository" -> go-pg, orm-rules · "do I need an ORM here?" -> orm-rules (answer: no, raw SQL)
