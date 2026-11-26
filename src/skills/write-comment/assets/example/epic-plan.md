## Architecture & Planning (`BULK-00`)

### Code analysis
- `src/orders/list.py:31`: the filter and permission query is built inside the handler; the other lists do the same.
- `web/src/components/ListToolbar.tsx`: every list page uses this toolbar, so one control covers them all.

### Core design decision (one export service, one query per list)
Each list moves its query into a function that both the list and its export call, so they cannot drift apart. One
service streams the CSV, caps the rows and escapes cells.

**Stack:** the current API and web stack and the standard library CSV writer; no new dependency or service.
**Rejected:** a background job with stored files: it adds a queue, storage and expiry for a need nobody has shown.

### Packages & Wave Order

| Wave | Issue | Scope | Key Owned Files | Gate |
|---|---|---|---|---|
| **Wave 1** | `#101` (`BULK-01`) | CSV stream, row cap, escaping | `src/export/stream.py` | `make verify` |
| **Wave 2** *(after #101)* | `#102` (`BULK-02`) | one export route per list | `src/*/list.py`, `src/*/export.py` | `make verify` |
| **Wave 3** *(after #102)* | `#103` (`BULK-03`) | download button and progress | `web/src/components/ListToolbar.tsx` | `cd web && npm run check` |

### Shared-File Sequencing Rules
- **`src/routes.py` (`BULK-02` vs any new route):** `BULK-02` rebases on `main` before it merges.

### Risks & Mitigations
- **A user exports rows they may not see:** list and export share one query, with a test per permission level.
- **A large export holds a database connection:** row cap and statement timeout.
- **Review:** each PR gets an independent review and the full checks.

Created: Architect (example)
