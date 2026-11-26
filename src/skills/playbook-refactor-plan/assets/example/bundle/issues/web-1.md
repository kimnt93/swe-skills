Lane: frontend
Wave: 1
Difficulty: simple
Priority: medium

## Goal
Every order screen builds its request parameters with one typed module.

## Analysis
`src/screens/OrderList.tsx`, `src/screens/OrderExport.tsx` and `src/screens/Dashboard.tsx` each turn screen state into
query parameters; two of them drop an empty status and one sends `status=`.

## Recommended solution
Add `src/orders/filter.ts` with an `OrderFilter` type and `toParams(filter)`, which omits empty fields, and use it on
the three screens. Rejected: a state library, which nothing else here needs.

## Read first
- `AGENTS.md`
- `src/screens/OrderList.tsx`

## Owned files (create or change only these)
- `src/orders/` (new)
- `src/screens/OrderList.tsx`
- `src/screens/OrderExport.tsx`
- `src/screens/Dashboard.tsx`

## Forbidden
- every file not listed above (report a needed change in the PR text instead)
- dependency files and lock files

## Depends on
- nothing; start now

## Notes
- Part of {{new:epic}}.

## Done when (run from the repository root on the committed head)
- `npm test -- filter`
- `make verify`

## Branch and PR
- Branch `ord-03/order-filter-module` from `main`; commits `refactor(ord-03): <summary>`; open a PR to `main`; do not
  merge it.

Created: CTO (example) / architect
