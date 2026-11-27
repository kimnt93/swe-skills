Lane: docs
Wave: 2
Difficulty: simple (one page about the merged limiter)
Priority: medium

## Goal
The API docs tell a client the limit, the `429` answer with `Retry-After` and what to do when it gets one.

## Read first
- `AGENTS.md`
- `docs/api.md`
- `src/api/ratelimit.py`

## Owned files (create or change only these)
- `docs/api.md`
- `CHANGELOG.md`

## Forbidden
- every file not listed above

## Depends on
- `RATE-00a` (#61) merged on `main`

## Notes
Refs #60. Contract with `RATE-00a`: `429`, `Retry-After` and `{"error":"RATE_LIMITED"}`.

## Done when (run from the repository root on the committed head)
- **Unit tests:** none: only documents change, there is no code to test
- **Functional tests:** none: only documents change, no behaviour does
- `make docs-check`

## Branch and PR
- Branch `rate-00c/limit-docs` from `main`; commits `docs(rate-00c): <summary>`; open a PR to `main`; do not merge it.

Created: CEO (example)
