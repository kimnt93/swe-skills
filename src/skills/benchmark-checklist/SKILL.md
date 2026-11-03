---
name: benchmark-checklist
description: "Vet a measured number (latency, throughput, memory, a speedup, a model score) before reporting or acting on it: what limits it, whether the work really happened, whether it repeats. Use after any benchmark, load test, profile comparison or ML evaluation."
metadata:
  group: process
  summary: "Vet a measured number before you report it or act on it"
---

# Benchmark checklist

Before you report or act on a number, answer each line. A "no" means the number is not ready.

1. **What limits it?** CPU, a lock, the database, the network, GC, the client, the partition count.
   Name it from a profile or a metric, not a guess.
2. **Did the work happen?** Count the work done (rows written, messages consumed, requests answered
   with 2xx) and the errors. A fast run full of errors measures the error path.
3. **Was it optimised away or cached?** Go: use `b.Loop()` or keep the result; Rust: `std::hint::black_box`;
   Python: no memoised result across iterations; HTTP: cache disabled or stated.
4. **Is it repeatable?** At least 5 runs; report the median and the spread.
   Go: `go test -bench . -count 10 | benchstat`. Python: `pytest-benchmark` stats. Rust: criterion's
   interval. Load: `k6`/`vegeta` with a fixed rate, warm-up excluded.
5. **Same conditions before and after?** Same machine, data size, build mode (`-race` off, release
   builds, `NODE_ENV=production`), same dataset split and seed for ML.
6. **Does it matter end to end?** A 3x faster function in a path that is 2% of the request is a 1%
   win. Measure the user-visible number too (p95 of the endpoint, the job's wall time, the page's LCP).
7. **For ML:** a fixed validation split, the metric with a confidence interval or several seeds, and
   no leakage from the test set.

Report: `metric: before → after (median of N, spread), limited by X, work done Y, errors Z`.
