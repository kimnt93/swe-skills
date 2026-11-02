### Profiling

**Read the profile; don't re-run it until you understand it.**

| Language | CPU | Memory | Concurrency |
|---|---|---|---|
| Go | `go tool pprof -top`/`-http` on `/debug/pprof/profile` or a `-cpuprofile` | `heap`, `allocs` profiles | `goroutine`, `block`, `mutex` profiles; `go tool trace` |
| Python | `py-spy record -o out.svg --pid <pid>` or `py-spy top` | `memray run`, `tracemalloc` | `py-spy dump` for stuck threads |
| Rust | `cargo flamegraph`, `perf record -g` | `heaptrack`, `dhat` | `tokio-console` for async tasks |
| Frontend | Chrome DevTools Performance, React Profiler | DevTools heap snapshot | — |

1. Identify the format and open it with the matching tool. Large profiles go to a subagent (the
   **guard-the-context-window** principle); keep the finding.
2. Find the frames with the most time (or the biggest retainers for memory) and walk to the hot path.
3. Map the hot frame to `file:line`. A frame without symbols is not a diagnosis yet.
4. With a before and an after profile, diff them to confirm. Without one, report the strongest
   hypothesis the profile supports, labelled as such.
5. Hand back the diagnosis; fix through [perf-issue](perf-issue.md) or [bug-fix](bug-fix.md).

**Reply:** the artefact, the hot path at `file:line`, the evidence, confirmed or hypothesis.
