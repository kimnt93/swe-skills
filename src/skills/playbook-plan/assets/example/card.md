Lane: backend
Wave: Backlog (Priority: low, queued after the open order-search card)
Difficulty: medium (an endpoint and a button; the limits need a decision)
Priority: low

## Goal
A user who filtered the order list can download exactly those orders as a CSV file.

## Read first
- `AGENTS.md`
- `ARCHITECTURE.md`
- `src/orders/list.py`
- `web/src/pages/Orders.tsx`

## Scope (high-level)
- The export uses the same filters and permissions as the list.
- A download action on the orders page.
- Out of scope: other file formats and scheduled exports.

## Depends on
- nothing strictly

## Done when
- `make verify`
- `cd web && npm run check`

## Notes
The architect's plan comment on this issue holds the approach, the package breakdown and the safety rules.

Created: CTO (example)
