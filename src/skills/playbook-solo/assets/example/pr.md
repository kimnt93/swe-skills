Closes #72

## Why
A user cannot cancel an order that is still open.

## What changed
- `DELETE /v1/orders/{id}` in `src/orders/cancel.py` cancels an open order and answers `409` for a filled one.
- `CHANGELOG.md` entry.

## Scope
Cancelling one order. The web button is the next issue, which depends on this one.

## Blast radius
Only open orders of the caller change; no schema, dependency or outbound change.

## Verification
- **Unit tests:** `tests/test_cancel_rule.py`, in `make verify`: open, filled and already cancelled, 3 passed
- **Functional tests:** `tests/functional/test_cancel_http.py` calls the route on a local app with a throwaway
  database: `200`, then `409` for a filled order, 2 passed
- `make verify` on the committed head: 61 passed
- Self-check (playbook-solo), **self-check, not an independent review**: `security_scan.py` on this head listed no item;
  the diff adds no outbound path; no proven finding

Created: Developer (example)
