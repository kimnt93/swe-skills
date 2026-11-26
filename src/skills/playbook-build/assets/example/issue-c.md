Lane: test
Wave: 2
Difficulty: simple (one load test against the merged limiter)
Priority: medium

## Goal
A load test shows one key getting `429` after 600 requests in a minute while a second key is still served.

## Read first
- `AGENTS.md`
- `tests/load/README.md`

## Owned files (create or change only these)
- `tests/load/test_ratelimit_load.py`
- `CHANGELOG.md`

## Forbidden
- every file not listed above

## Depends on
- `RATE-00a` (#61) merged on `main`

## Notes
Refs #60. Contract with `RATE-00a`: `429`, `Retry-After` and `{"error":"RATE_LIMITED"}`.

## Done when (run from the repository root on the committed head)
- `make load-test`

## Branch and PR
- Branch `rate-00c/load-test` from `main`; commits `test(rate-00c): <summary>`; open a PR to `main`; do not merge it.

Created: CEO (example)
