Lane: backend
Wave: 1
Difficulty: medium (a middleware across two files and its tests)
Priority: medium

## Goal
A request over its API key's limit gets `429`, `Retry-After: <seconds>` and `{"error":"RATE_LIMITED"}`; other keys are
served as before; a bucket idle for 10 minutes is dropped (plan v1 on #60).

## Read first
- `AGENTS.md`
- `src/api/app.py`
- `src/api/auth.py`

## Owned files (create or change only these)
- `src/api/ratelimit.py`
- `src/api/app.py`
- `tests/test_ratelimit.py`
- `tests/load/test_ratelimit_load.py`
- `CHANGELOG.md`

## Forbidden
- every file not listed above

## Depends on
- nothing; start now

## Notes
Refs #60. Contract with `RATE-00b` and `RATE-00c`: `RATE_LIMIT_PER_MINUTE` (default 600) and `RATE_LIMIT_BURST`
(default 100); over the limit `429` with `Retry-After` and `{"error":"RATE_LIMITED"}`.

## Done when (run from the repository root on the committed head)
- **Unit tests:** `make verify` runs `tests/test_ratelimit.py`: at the limit, one over it, one bucket per key
- **Functional tests:** `make load-test` runs the app on a local port: one key gets `429` after the limit while a second key is served
- `make verify`

## Branch and PR
- Branch `rate-00a/limit-per-key` from `main`; commits `feat(rate-00a): <summary>`; open a PR to `main`; do not merge it.

Created: CEO (example)
