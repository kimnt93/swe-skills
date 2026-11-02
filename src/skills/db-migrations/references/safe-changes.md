# Safe schema changes

*Verified on PostgreSQL 17 with goose 3.28: every pattern below was applied, rolled back and re-applied; the backfill ran on 12,000 rows.*

The service keeps serving while a migration runs, and during a rolling deploy the **old and new code both run against the new schema**. So a safe change is one the previous release still works with. Write the SQL in the readable layout (one clause per line, one column per line).

## Quick table

| Change | Safe pattern | Unsafe version |
|---|---|---|
| New table | `CREATE TABLE`, columns `NOT NULL DEFAULT ...` where a default exists, index in the same file | nullable everything, no index |
| Add a column | `ADD COLUMN c type NOT NULL DEFAULT x` (fast on PostgreSQL 11+ for constant defaults) | `ADD COLUMN c type NOT NULL` with no default (fails on a non-empty table) |
| Add a unique/lookup index on an existing table | `CREATE INDEX CONCURRENTLY` in a `NO TRANSACTION` file | plain `CREATE INDEX` (blocks writes) |
| Add a foreign key / check on a big table | `ADD CONSTRAINT ... NOT VALID`, then `VALIDATE CONSTRAINT` in a later file | one `ADD CONSTRAINT` (long lock) |
| Make a column `NOT NULL` | add a `CHECK (c IS NOT NULL) NOT VALID`, validate, then `SET NOT NULL` | `SET NOT NULL` directly on a big table |
| Backfill data | batches of a few thousand rows, each its own transaction | one `UPDATE` of the whole table |
| Rename a column or table | expand and contract (below) | `RENAME` while the old release still reads the old name |
| Drop a column or table | after no release reads it (contract step), with `-- destructive: reason` | dropping in the same release that stops using it |
| Change a column type | new column, dual write, backfill, switch reads, drop the old | `ALTER COLUMN TYPE` (rewrites and locks the table) |

## Add a column

```sql
-- +goose Up
ALTER TABLE orders
    ADD COLUMN status text NOT NULL DEFAULT 'open';

-- +goose Down
ALTER TABLE orders
    DROP COLUMN status;
```

A default keeps the column never-NULL, so the Go struct, Python dataclass or Rust type needs no pointer or `Option` (`assets/templates/0002_orders_add_status.sql`).

## Index on an existing table

```sql
-- +goose NO TRANSACTION

-- +goose Up
CREATE INDEX CONCURRENTLY IF NOT EXISTS orders_status_idx
    ON orders (status);

-- +goose Down
DROP INDEX CONCURRENTLY IF EXISTS orders_status_idx;
```

A failed `CONCURRENTLY` build leaves an `INVALID` index: drop it and re-run (`IF NOT EXISTS` alone would keep the invalid one). `scripts/check_migrations.py` rejects a plain `CREATE INDEX` on a table the file did not create.

## Backfill in batches

`assets/templates/0004_orders_backfill_note.sql` loops `UPDATE ... WHERE id IN (SELECT id ... LIMIT n)` and commits per batch, in a `NO TRANSACTION` file with a `StatementBegin` block. It only touches rows that still need the change, so a re-run (or a crash and restart) continues where it stopped. For very large tables run the backfill as a separate job after the deploy instead of inside the migration.

## Rename or drop: expand and contract

Three releases (or three files across two releases) instead of one `RENAME`:

1. **Expand**: add the new column (or table) with a default; deploy code that **writes both** and reads the new one, falling back to the old.
2. **Backfill**: copy the old values in batches; verify counts match.
3. **Contract**: after no running release reads the old column, drop it in its own migration:

```sql
-- +goose Up
-- destructive: no release reads orders.qty since 2026.10 (replaced by quantity, 0009)
ALTER TABLE orders
    DROP COLUMN qty;

-- +goose Down
-- irreversible: the dropped values are not recorded; restore from backup if needed.
SELECT 1;
```

## Review checklist

- [ ] The previous release still works with the new schema.
- [ ] No long lock: indexes concurrent, constraints `NOT VALID` then validated, backfill batched.
- [ ] Down works, or the step says `-- irreversible: reason`; a drop says `-- destructive: reason`.
- [ ] The model, SQL constants, port and tests changed in the same pull request.
- [ ] `python3 scripts/check_migrations.py schemas` is clean, and `up`, `down`, `up` ran on a disposable PostgreSQL.
- [ ] The SQL reads like the `readable-code` examples: one clause and one column per line, comments explain why.
