Lane: backend
Wave: 1
Difficulty: medium (two copies of one rule, no schema change)
Priority: medium

## Goal
One function in `internal/orders` takes an order filter and returns the matching orders, covered by tests.

## Analysis
`internal/http/orders.go` builds the list's `WHERE` clause inline. `internal/export/csv.go` builds a second one and
treats an empty status as "open only", while the list treats it as "any". That difference is the defect users report.

## Recommended solution
Add `orders.Filter` and `orders.Find(ctx, filter)` in `internal/orders/query.go` with parameterised SQL. Take the
list's meaning for every field: it is the one users see. Rejected: a database view, because the filter is dynamic.

## Read first
- `AGENTS.md`
- `internal/http/orders.go`
- `internal/export/csv.go`

## Owned files (create or change only these)
- `internal/orders/` (new package: `query.go`, `query_test.go`)

## Forbidden
- every file not listed above (report a needed change in the PR text instead)
- `schemas/` and the callers: they move in the next wave

## Depends on
- nothing; start now

## Notes
- Part of {{new:epic}}.
- Contract for the next wave: `Filter{Status []string; From, To time.Time; AccountID string}`; an empty field
  filters nothing.

## Done when (run from the repository root on the committed head)
- `go test ./internal/orders/...`
- `make verify`

## Branch and PR
- Branch `ord-01/order-query` from `main`; commits `refactor(ord-01): <summary>`; open a PR to `main`; do not merge it.

Created: CTO (example) / architect
