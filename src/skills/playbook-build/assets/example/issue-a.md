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
- `CHANGELOG.md`

## Forbidden
- every file not listed above

## Depends on
- nothing; start now

## Notes
Refs #60. Contract with `RATE-00b` and `RATE-00c`: `RATE_LIMIT_PER_MINUTE` (default 600) and `RATE_LIMIT_BURST`
(default 100); over the limit `429` with `Retry-After` and `{"error":"RATE_LIMITED"}`.

## Done when (run from the repository root on the committed head)
- `make verify`

## Branch and PR
- Branch `rate-00a/limit-per-key` from `main`; commits `feat(rate-00a): <summary>`; open a PR to `main`; do not merge it.

Created: CEO (example)
