Lane: backend
Wave: 2
Difficulty: medium (two callers and their tests)
Priority: medium

## Goal
The list handler and the CSV export return the same orders for the same parameters, through `orders.Find`.

## Analysis
Both callers build SQL themselves: `internal/http/orders.go` and `internal/export/csv.go`. The export's tests in
`internal/export/csv_test.go` assert the "open only" default, which is the behaviour this change removes.

## Recommended solution
Parse the request into `orders.Filter` in each handler, call `orders.Find`, and delete both inline queries. Change the
export test to the list's meaning and add one test that sends both endpoints the same parameters.

## Read first
- `internal/orders/query.go`
- `internal/http/orders.go`
- `internal/export/csv.go`

## Owned files (create or change only these)
- `internal/http/orders.go`
- `internal/http/orders_test.go`
- `internal/export/csv.go`
- `internal/export/csv_test.go`

## Forbidden
- every file not listed above (report a needed change in the PR text instead)
- `internal/orders/`: ask for a plan change if the query is not enough

## Depends on
- {{new:api-1}} merged

## Notes
- Part of {{new:epic}}.

## Done when (run from the repository root on the committed head)
- **Unit tests:** `go test ./internal/http/... ./internal/export/...`: each handler's filter
- **Functional tests:** `go test -tags e2e ./internal/http/... ./internal/export/...` sends both routes of a local server, on a throwaway database, the same parameters
- `go test ./internal/http/... ./internal/export/...`
- `make verify`

## Branch and PR
- Branch `ord-02/shared-order-callers` from `main`; commits `refactor(ord-02): <summary>`; open a PR to `main`; do not
  merge it.

Created: CTO (example) / architect
