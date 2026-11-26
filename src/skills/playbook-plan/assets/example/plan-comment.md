## Architecture & Planning (`EXPORT-00` — Priority: Low)

### Code analysis
- `src/orders/list.py:31`: the filter and permission query is built inside the list handler, so nothing can reuse it.
- `src/orders/list.py:58`: returns pages of 50; no path returns the whole filtered set.
- `web/src/pages/Orders.tsx:74`: the active filters are in the page URL, so a download can send them unchanged.

### Core design decision
Move the filter and permission query into `order_query(filters, user)`, used by both the list and a new
`GET /v1/orders/export` that streams `text/csv` in one read transaction, so the two cannot drift apart. Columns
`id,created_at,customer,status,total,currency`; times in RFC 3339 UTC; over the row cap: `422 EXPORT_TOO_LARGE`.

**Stack:** the current API and web stack and the standard library CSV writer; no new dependency, service or table.
**Rejected:** building the CSV in the browser from the paged list: one request per page, growing memory, and rows can
move between pages while it runs.

### Planned Packages (split into child cards when promoted)
1. **`EXPORT-00a` (Backend export route):** extract `order_query` into `src/orders/query.py` with the list tests
   unchanged; add `src/orders/export.py` with the row cap and formula-cell escaping, and a test per permission level.
2. **`EXPORT-00b` (Web download button):** add the button in `web/src/pages/Orders.tsx`, sending the filters from the
   page URL, and show the `EXPORT_TOO_LARGE` message.

### Risks & Gates
- **A user exports rows they may not see:** list and export share one query, tested per permission level.
- **A large export holds a database connection:** row cap and statement timeout.
- **Gates:** `make verify` + `cd web && npm run check` + an independent review of `EXPORT-00a`.

### Decisions
1. The row cap: 50,000. Reason: recommended; it is one constant to raise, and a larger export holds the connection longer.
2. The customer's email as a column: no. Reason: the issue does not ask for it, and adding it later is small.

Created: Architect (example)
