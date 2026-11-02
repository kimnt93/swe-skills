<!-- applies: Apply before trusting, reporting or acting on a measured number: latency, throughput, memory, a speedup, a backtest result. -->
# Explain the Number

Find what limits the number and rule out that it measured something else.

- What bounds it: CPU, the database, the network, a lock, the client, the Kafka partition count, GC?
- Is the work real: did the benchmark actually hit PostgreSQL, did the loop get optimised away (`b.Loop()` / `black_box`), did the cache serve every request?
- Repeat it: several runs, the median and the spread (`benchstat` for Go, `pytest-benchmark` stats, `criterion` for Rust).
- Run the **benchmark-checklist** skill before you report it.
