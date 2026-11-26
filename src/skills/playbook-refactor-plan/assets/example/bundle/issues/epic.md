Lane: backend
Wave: 0 (Epic)
Difficulty: medium
Priority: medium

## Goal
The order list, the CSV export and the web screens filter orders by one rule, so they show the same orders.

## Reference Architecture
`internal/orders` owns the filter and its query. Handlers parse a request into that filter and format the result; the web
app builds the same filter in one typed module.
1. **Query (`ORD-01`):** one filter type and one query function, with its tests.
2. **Callers (`ORD-02`):** the list and export handlers call it and lose their own SQL.
3. **Web (`ORD-03`):** one module turns screen state into the request parameters.

## Scope (high-level)
- In: where the filter lives and who calls it. Behaviour stays as the list behaves today.
- Out: new filters, pagination changes and retention (`#18` stays open).

## Done when
Every child is merged and `make verify` passes on `main` in both repositories.

## Notes
- Wave 1: {{new:api-1}} and {{new:web-1}} (different repositories, no shared contract change).
- Wave 2: {{new:api-2}}, after {{new:api-1}} is merged.
- Replaces `#12` and `#15` here, and the web repository's filter issues.

Created: CTO (example) / architect
