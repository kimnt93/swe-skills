<!-- applies: Apply when concurrent actors (goroutines, async tasks, threads, consumers, workers) might write the same row, key, file or branch. -->
# Separate Before Serializing Shared State

First remove the sharing; add a lock only when one writer is a real invariant.

- Partition: Kafka partitions keyed by account or symbol, so one consumer owns one key; per-worker Redis keys merged at read time; one worktree per agent.
- Per-actor state merged at the read boundary beats a global mutex.
- When a single writer is the invariant (an account balance), make it structural: one owner goroutine or task, `SELECT ... FOR UPDATE`, or an optimistic `version` column, and test the race (`go test -race`, a concurrent pytest, `loom` for Rust).
