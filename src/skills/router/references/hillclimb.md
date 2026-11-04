### Hillclimb

**One change, one measurement, keep or revert.** For pushing one metric to a target over many
iterations (latency, throughput, memory, a model's validation score).

1. Fix the metric, its direction, and a stop predicate with a floor on attempts ("p95 under 20 ms,
   and at least 8 attempts"). Pick a workload that reproduces the complaint.
2. Build the measurement harness and freeze it: one command, median of N runs, prints its error
   count and the work done (the **build-the-lever** principle). Vet it with the
   **explain-the-number** principle. Record the baseline and a green run of the regression tests.
3. Keep a decision log outside the tree: one row per attempt (hypothesis, change, before, after,
   kept or reverted).
4. Each hypothesis names a mechanism ("the JSON encode allocates per field") ordered as in
   [perf-issue](perf-issue.md) step 3. For ML, a hypothesis is one change to data, features or the
   model, evaluated on a fixed validation split with a fixed seed.
5. Loop: a subagent on the `mid` tier makes the change in its own worktree; measure; keep it only if
   the metric moves past the noise and the tests stay green; otherwise revert fully. One commit per
   kept win.
6. On a plateau, change category before giving up. Correctness and simplicity outrank the number.
7. Stop at the predicate. Never relax it to finish. Then [opening-a-pr](opening-a-pr.md).

**Reply:** metric, baseline → final, attempts kept / reverted, each kept win in one line, the next idea.
