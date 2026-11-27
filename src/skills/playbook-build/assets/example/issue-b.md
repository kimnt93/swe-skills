Lane: ops
Wave: 1
Difficulty: simple (two settings in one deployment file)
Priority: medium

## Goal
The API service runs with `RATE_LIMIT_PER_MINUTE=600` and `RATE_LIMIT_BURST=100` in staging and production.

## Read first
- `AGENTS.md`
- `deploy/compose.yaml`

## Owned files (create or change only these)
- `deploy/compose.yaml`
- `CHANGELOG.md`

## Forbidden
- every file not listed above

## Depends on
- nothing; start now (the names are the contract, so it does not wait for `RATE-00a`)

## Notes
Refs #60. Contract with `RATE-00a`: `RATE_LIMIT_PER_MINUTE` and `RATE_LIMIT_BURST`, both integers.

## Done when (run from the repository root on the committed head)
- **Unit tests:** none: two settings in one deployment file, there is no code to test
- **Functional tests:** `docker compose -f deploy/compose.yaml config --quiet` renders the real deployment file on this machine
- `make verify`

## Branch and PR
- Branch `rate-00b/deploy-limits` from `main`; commits `chore(rate-00b): <summary>`; open a PR to `main`; do not merge it.

Created: CEO (example)
