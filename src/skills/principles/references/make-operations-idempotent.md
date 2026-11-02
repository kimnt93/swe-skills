<!-- applies: Apply when designing a Kafka consumer, a retry, a job, a migration step, or any handler that can run twice after a crash. -->
# Make Operations Idempotent

The same input applied twice gives the same end state.

- Kafka is at-least-once: dedup by a stable key (`fill_id`, `event_id`) with a unique constraint and `INSERT ... ON CONFLICT DO NOTHING`, or a Redis `SET NX` lock with a TTL longer than the handler.
- Commit the consumer offset after the database transaction commits, never before.
- Upserts over inserts for state that converges (positions, snapshots).
- Migrations and backfills are re-runnable: `IF NOT EXISTS`, batches keyed by id, a marker of the last done batch.
- Prove it: send the duplicate in a test (`replay.py check --mutate duplicate`).
