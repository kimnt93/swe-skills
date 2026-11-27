Lane: frontend
Wave: 2
Difficulty: simple (formatting in one page)
Priority: medium
Pipeline: quick

## Goal
The order list shows each time in the user's local zone with the zone's short name.

## Read first
- `AGENTS.md`
- `web/src/pages/Orders.tsx`

## Owned files (create or change only these)
- `web/src/pages/Orders.tsx`
- `web/src/pages/Orders.test.tsx`
- `web/e2e/orders.spec.ts`
- `CHANGELOG.md`

## Forbidden
- every file not listed above

## Depends on
- `ORD-01` (#51) merged

## Notes
Refs #50. Contract with `ORD-01`: field `created_at`, RFC 3339, UTC with `Z`, no fractions.

## Done when (run from the repository root on the committed head)
- **Unit tests:** `cd web && npm run check` runs `web/src/pages/Orders.test.tsx`: the format in a fixed zone
- **Functional tests:** `cd web && npm run test:e2e -- orders` opens the order list in a local browser against a fake API: local time and zone name
- `cd web && npm run check`

## Branch and PR
- Branch `ord-02/local-order-times` from `main`; commits `fix(ord-02): <summary>`; open a PR to `main`; do not merge it.

Created: CTO (example)
