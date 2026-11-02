# goose workflow

*Verified with: goose 3.28 (CLI and `pressly/goose/v3` library), PostgreSQL 17: `up`, `status`, `down`, `up-to`, `reset`, `NO TRANSACTION` with `CREATE INDEX CONCURRENTLY`, and a `StatementBegin` block with `COMMIT` inside.*

goose applies `schemas/NNNN_name.sql` files in order and records each in the `goose_db_version` table. Plain SQL, no framework: the same files serve Go, Python and Rust services.

## File format

```sql
-- +goose Up
ALTER TABLE items
    ADD COLUMN label text NOT NULL DEFAULT '';

-- +goose Down
ALTER TABLE items
    DROP COLUMN label;
```

- `-- +goose Up` first, then `-- +goose Down`. Statements end with `;`, one per line start.
- `-- +goose NO TRANSACTION` at the top of the file runs each statement outside a transaction (needed for `CREATE INDEX CONCURRENTLY`, `ALTER TYPE ... ADD VALUE`, and a `DO` block that must `COMMIT`).
- `-- +goose StatementBegin` / `StatementEnd` wrap a statement that contains `;` inside (a function body, a `DO $$ ... $$` block).
- Numbering `0001`, `0002`, ...: contiguous, no gaps. Two branches that both add `0007` conflict at merge: renumber the later one before release.

Templates (all four applied live): `assets/templates/0001_create_orders.sql` (new table and its index), `0002_orders_add_status.sql` (add a column with a default), `0003_orders_status_index.sql` (concurrent index), `0004_orders_backfill_note.sql` (batched backfill).

## Commands

```bash
export GOOSE_DRIVER=postgres
export GOOSE_DBSTRING="postgres://$POSTGRES_USER:$(cat "$POSTGRES_PASSWORD_FILE")@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB?sslmode=$POSTGRES_SSLMODE"
export GOOSE_MIGRATION_DIR=schemas

goose status            # applied and pending
goose up                # apply everything pending
goose up-to 3           # stop at version 3
goose down              # roll back one version
goose reset             # roll back everything (disposable databases only)
goose create add_status sql    # scaffold the next file
```

Install: `go install github.com/pressly/goose/v3/cmd/goose@latest`, or `docker run` an image with the binary in the migration job. Never put the password on a command line that is logged; build the DSN from the secret file inside the job.

## Run it from the service (Go)

The Go template embeds goose (`go-code/assets/template/internal/infrastructure/postgres/migrate.go`): `postgres.Migrate(ctx, cfg, "schemas")` opens `database/sql` with pgx's stdlib driver (migrations only; the service itself uses go-pg or bun) and calls `goose.UpContext`. The binary exposes it as `api migrate`, a one-shot command.

Python and Rust services run the `goose` binary in the job image; their tests apply the `Up` section directly (the scaffold's integration tests do this) so the unit of truth stays the SQL file.

## Where it runs

- **One one-shot job per deploy**, before the services that depend on the schema: `restart_policy: none`, completion gate, never a parallel matrix entry and never from each replica (`deployment-setup`: `migration_compose_file`, `swarm-compose`, `multi-service-pipelines`).
- Locking: the goose CLI does not lock against concurrent runners (the library's `Provider` has an optional session locker). The single job is the lock; do not start two.
- Roll forward, not back, in production: a failed release is fixed with a new migration; `down` is for development and for the rare emergency with a reviewed plan.

## Testing a migration

1. Start a disposable PostgreSQL (`docker compose -f docker-compose.infra.local.yaml up -d postgres`; database name `app`, `test` or `e2e`).
2. `goose up`, then load representative rows if the change touches data, then `goose down`, then `goose up` again.
3. Run the service's integration tests (they apply the same files).
4. `python3 scripts/check_migrations.py schemas` for the structural rules.

## Related

[safe-changes](safe-changes.md) · [orm-tools](orm-tools.md) · `deployment-setup` · the language skills' `postgres` references.
