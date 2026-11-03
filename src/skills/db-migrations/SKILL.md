---
name: db-migrations
description: Write, review and run PostgreSQL schema migrations for Go, Python and Rust services. The default is versioned raw SQL files run by goose (schemas/NNNN_name.sql with Up and Down), applied by a one-shot job before the service rolls out. Covers safe changes (add a column, backfill in batches, create an index concurrently, rename or drop with expand and contract), readable SQL layout, testing a migration against a disposable database, a migration linter script, and how this fits an ORM project (Alembic, sea-orm-migration, bun migrations only when the project already uses them).
metadata:
  group: data
  summary: "PostgreSQL schema changes as goose SQL files, safe by default"
---

# Database migrations

**The default is raw SQL files run by goose.** Every service in this stack keeps its schema in `schemas/NNNN_name.sql`: immutable, ordered, readable SQL, applied by a one-shot job before the service rolls out. An ORM never owns the schema (see `db-orm`); only keep an ORM's own migration tool when the project already uses it.

## How to work

1. **Discover the project**: the `schemas/` directory, the numbering, how the job runs (`api migrate`, the goose binary, `deployment-setup` `migration_compose_file`), and any ORM migration tool already in use. Follow what exists.
2. **Never edit a released file.** A change is a new file with the next number. Released means merged, deployed or applied anywhere shared.
3. **Pick the change pattern** in [safe-changes](references/safe-changes.md) before writing the SQL: most mistakes are the pattern, not the syntax.
4. **Write the file** from `assets/templates/` and the layout rules below; **write the Down** or mark the step `-- irreversible: reason`.
5. **Update the model in the same change**: row struct / dataclass / entity, SQL constants, port, tests (language skill `postgres` reference).
6. **Verify** with the commands below, then report what ran. A migration that was never applied to a real PostgreSQL is not verified.

## Which reference to read

| The request mentions | Read |
|---|---|
| goose, running migrations, `up`/`down`/`status`, CI and Swarm job, per-language runner | [goose](references/goose.md) |
| add or change a column, index, constraint, backfill, rename, drop, large table, zero downtime | [safe-changes](references/safe-changes.md) |
| Alembic, `sea-orm-migration`, bun migrations, "the ORM generates the schema" | [orm-tools](references/orm-tools.md) |
| the service's SQL, models, ORM | the language skill's `postgres` reference, or `db-orm` |
| the migration job in compose / CI | the `deployment-setup` skill |

## Rules that always apply

- **File**: `schemas/NNNN_snake_case.sql` (four digits, contiguous from `0001`), `-- +goose Up` first, then a working `-- +goose Down`.
- **Immutable**: add a version, never rewrite one. Fix a bad migration with a new one.
- **Safe by default**: new columns are `NOT NULL DEFAULT ...` (or nullable, backfilled, then tightened); indexes on existing tables are `CREATE INDEX CONCURRENTLY` in a `-- +goose NO TRANSACTION` file; a rename or drop uses expand and contract over two releases.
- **One job runs them**, once per deploy, before the dependent services start: never from every replica and never from an entrypoint of the service.
- **Readable SQL**: keywords upper case, one clause per line, one column per line, 4-space indent, at most 100 columns, no tabs, one statement per line; comments say why. Same layout as the language skills' `readable-code` SQL rules.
- **No conversions that belong in the model**: a migration defines types; it does not exist to make `SELECT` return a different type.
- **Secrets**: the job reads `POSTGRES_*` from the environment (`POSTGRES_PASSWORD` or `_FILE`); the DSN is never logged or committed.
- **Test on a real database**: apply `up`, `down`, `up` on a disposable PostgreSQL, never on shared data. Destructive steps need `-- destructive: reason`.

## Verify

```bash
python3 scripts/check_migrations.py schemas              # naming, Up/Down, concurrent indexes, NOT NULL defaults, layout
goose -dir schemas postgres "$DSN" up && goose -dir schemas postgres "$DSN" down && goose -dir schemas postgres "$DSN" up
python3 scripts/check_migrations.py --self-test          # prove the checker itself works
```

`DSN` points at a disposable database (`docker compose -f docker-compose.infra.local.yaml up -d postgres`). The templates in `assets/templates/` pass the linter and were applied, rolled back and re-applied on PostgreSQL 17 (the batched backfill with 12,000 rows).

## Example prompts

- "add a status column to orders" -> safe-changes, goose · "add an index on a big table" -> safe-changes (CONCURRENTLY)
- "rename a column without downtime" -> safe-changes (expand and contract) · "the ORM should create the tables" -> orm-tools (no)
