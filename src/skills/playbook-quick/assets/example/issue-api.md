Lane: backend
Wave: 1
Difficulty: simple (one serializer and its test)
Priority: medium
Pipeline: quick

## Goal
The order API returns `created_at` as RFC 3339 in UTC, for example `2026-03-01T09:30:00Z`.

## Read first
- `AGENTS.md`
- `src/orders/serialize.py`

## Owned files (create or change only these)
- `src/orders/serialize.py`
- `tests/test_order_serialize.py`
- `CHANGELOG.md`

## Forbidden
- every file not listed above

## Depends on
- nothing; start now

## Notes
Refs #50. Contract with `ORD-02`: field `created_at`, RFC 3339, UTC with `Z`, no fractions.

## Done when (run from the repository root on the committed head)
- **Unit tests:** `make verify` runs `tests/test_order_serialize.py`: the UTC format
- **Functional tests:** `make verify` runs its order-route case there, on a local test server with a throwaway database: `created_at` is UTC
- `make verify`

## Branch and PR
- Branch `ord-01/utc-created-at` from `main`; commits `fix(ord-01): <summary>`; open a PR to `main`; do not merge it.

Created: CTO (example)
