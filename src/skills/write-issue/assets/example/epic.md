Lane: backend
Wave: 0 (Epic)
Difficulty: hard
Priority: medium

## Goal
A user can export any list in the product (orders, customers, invoices) and download it, with live progress for large
exports.

## Reference Architecture
One export service with one query per list, and one download control reused by every page.
1. **Shared export service (`BULK-01`):** streaming CSV writer, row cap and cell escaping.
2. **List endpoints (`BULK-02`):** one export route per list, using that list's own query and permissions.
3. **Web control (`BULK-03`):** the download button with progress and errors.

## Done when
All `BULK-01`..`BULK-03` child issues are reviewed PASS and merged to `main`, and `make verify` and
`cd web && npm run check` pass on `main`.

Created: CTO (example)
