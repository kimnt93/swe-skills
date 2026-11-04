### Migration

**You own the data. Every step stays reversible until the last one, and each one is proven on a
live database.** For PostgreSQL schema changes as goose SQL files, follow the `db-migrations` skill.

1. Name the end state: the tables, columns, indexes and constraints after the change, and every
   reader and writer of the touched tables (search the code, the SQL constants and the Kafka
   consumers).
2. Split into **expand → migrate → contract**. Each phase is its own commit (or PR) that leaves the
   system working with both old and new code running:
   - expand: add nullable or defaulted columns, new tables, and indexes with `CONCURRENTLY`;
   - migrate: dual-write, then backfill in batches, then switch reads;
   - contract: drop the old columns or tables, marked `-- destructive: reason`.
3. Run `python3 <db-migrations>/scripts/check_migrations.py schemas` on every file. Zero findings.
4. Prove each phase on a live PostgreSQL (the service's local infra compose): migrate up, run the
   service's tests, migrate down, migrate up again. Paste the commands and their output.
5. For a backfill, measure rows per second on a realistic copy and state the expected wall time
   and lock behaviour before it runs anywhere shared (the **explain-the-number** principle).
6. Money-path tables (orders, fills, positions, balances) go to the `developer-senior` agent, and the contract phase
   needs a human go.
7. Run [opening-a-pr](opening-a-pr.md), one PR per phase.

**Reply:** the end state, the phases with their PRs, the proof per phase, the backfill numbers,
and what still needs a human go.
