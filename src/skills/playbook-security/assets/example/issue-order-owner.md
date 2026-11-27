Lane: backend
Wave: 1
Difficulty: hard (authorization)
Priority: high

## Goal
Only the account that owns an order can read it; anyone else gets 404.

## Read first
- `AGENTS.md`
- `api/orders.py:31`

## Owned files (create or change only these)
- `api/orders.py`
- `tests/test_orders_access.py` (new)

## Forbidden
- every file not listed above (report a needed change in the PR text instead)
- dependency files and lock files

## Depends on
- nothing; start now

## Notes
- No new outbound path.

## Done when (run from the repository root on the committed head)
- **Unit tests:** `pytest -q tests/test_orders_access.py -k rule` runs the ownership rule alone
- **Functional tests:** `pytest -q tests/test_orders_access.py` calls the route on a local app with a throwaway database
- `pytest -q tests/test_orders_access.py` passes, and fails without the change: user B gets 404 for user A's order.
- `make verify`

## Branch and PR
- Branch `sec-01/order-owner` from `main`; commits `fix(sec-01): <summary>`; open a PR to `main`; do not merge it.

Created: Reviewer (example) / auditor
