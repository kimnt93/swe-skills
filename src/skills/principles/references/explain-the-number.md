<!-- applies: Apply before trusting, reporting or acting on a measured number: latency, throughput, memory, a speedup, a backtest result. -->
# Explain the Number

Find what limits the number and rule out that it measured something else.

- What bounds it: CPU, the database, the network, a lock, the client, the Kafka partition count, GC?
- Is the work real: did the benchmark actually hit PostgreSQL, did the loop get optimised away (`b.Loop()` / `black_box`), did the cache serve every request?
- Repeat it: several runs, the median and the spread (`benchstat` for Go, `pytest-benchmark` stats, `criterion` for Rust).
- Did the work happen: count the work done (rows written, messages consumed, 2xx answered) and the errors. A fast run full of errors measures the error path.
- Same conditions before and after: machine, data size, build mode (`-race` off, release builds, `NODE_ENV=production`), dataset split and seed for ML.
- Does it matter end to end: a 3x faster function in 2% of the request is a 1% win. Measure the user-visible number too (endpoint p95, job wall time, LCP).
- ML: a fixed validation split, the metric over several seeds or with an interval, no leakage from the test set.
- Report it as `metric: before -> after (median of N, spread), limited by X, work done Y, errors Z`.
