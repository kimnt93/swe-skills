## Architecture & Planning (`RATE-00` — Priority: Medium)

### Code analysis
- `src/api/app.py:22`: every route is mounted on one app with a middleware list, so one middleware covers them all.
- `src/api/auth.py:41`: the API key is resolved before any handler runs and is on the request state.
- `deploy/compose.yaml:18`: the API service already reads its settings from environment variables.

### Core design decision
A token bucket per API key in `src/api/ratelimit.py`, added to the middleware list after authentication. Over the limit
it answers `429` with `Retry-After: <seconds>` and the body `{"error":"RATE_LIMITED"}`. The limits come from
`RATE_LIMIT_PER_MINUTE` (integer, default 600) and `RATE_LIMIT_BURST` (integer, default 100); these two names and the
`429` answer are the contract between the three packages.

**Stack:** the current API stack and the standard library; the buckets live in process memory. No new dependency,
service or table.
**Rejected:** a shared Redis counter: right for several replicas, but the API runs one replica today, and it adds a
network call to every request.

### Planned Packages (split into child cards when promoted)
1. **`RATE-00a` (Backend limiter):** `src/api/ratelimit.py`, its wiring in `src/api/app.py`, and
   `tests/test_ratelimit.py` with a test at the limit, one over it and one per key.
2. **`RATE-00b` (Deployment limits):** the two variables in `deploy/compose.yaml`, with the staging and production
   values.
3. **`RATE-00c` (Load test):** `tests/load/test_ratelimit_load.py`: 1,000 requests a minute from one key get `429`
   after the limit while a second key is served; needs `RATE-00a` on `main`.

### Risks & Gates
- **A client is cut off by mistake:** the defaults are above today's busiest key (410 a minute last month).
- **Memory grows with keys:** idle buckets are dropped after 10 minutes.
- **Gates:** `make verify` + `make load-test`.

### Decisions
1. The production limit: 600 a minute with a burst of 100. Reason: recommended; above today's busiest key, and a setting
   that is easy to change. Rolling it out to production is not part of this decision.

Created: Architect (example)
