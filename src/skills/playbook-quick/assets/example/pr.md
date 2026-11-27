Closes #52

## Why
The order list shows times in the server's zone, so users misread when an order was placed.

## What changed
- `web/src/pages/Orders.tsx` formats `created_at` in the browser's zone, with the zone's short name.
- `web/src/pages/Orders.test.tsx` covers it with a fixed zone; `web/e2e/orders.spec.ts` covers the page.
- `CHANGELOG.md` entry.

## Scope
The order list only. The API format is `ORD-01` (#51), already merged.

## Blast radius
Only how times are displayed on one page; no API, data or dependency changes.

## Verification
- **Unit tests:** `web/src/pages/Orders.test.tsx`, in `cd web && npm run check`: 42 tests passed
- **Functional tests:** `cd web && npm run test:e2e -- orders`: the order list in a local browser against a fake API
  shows local time and zone name, 1 passed
- `cd web && npm run check`: 42 tests passed

Created: Developer (example)
