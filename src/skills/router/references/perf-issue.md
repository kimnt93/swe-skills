### Perf issue

**Measure first. Fix from the profile, not a guess.**

1. Reproduce the slowness with a number: the endpoint's p95 (`hey`, `k6`, `vegeta`), a benchmark
   (`go test -bench`, `pytest-benchmark`, `cargo bench` with criterion), a job's wall time, a page's
   Web Vitals (Lighthouse, Playwright tracing). Record the baseline.
2. Profile the real workload and read it with the [profiling](profiling.md) playbook.
3. Fix in this order, stopping when the target is met:
   1. do less work (an N+1 query, a missing index, work repeated per row or per render);
   2. batch (one query instead of many, `COPY`, pipelined Redis, Kafka batching);
   3. cache (only with an invalidation rule you can state);
   4. a better algorithm or data structure;
   5. a faster language for the hot path: move it to Rust (a PyO3 binding for Python, a Rust service
      for Go), measured.
4. If the fix crosses a function boundary, run the **architect** skill first.
5. Measure again with the same harness; vet the number with the **explain-the-number** principle.
6. For a sustained push on one metric, use the [hillclimb](hillclimb.md) playbook.

**Reply:** baseline → after, the limiter, the fix, and the evidence the number is real.
