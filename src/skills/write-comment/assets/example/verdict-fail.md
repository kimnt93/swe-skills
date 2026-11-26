Verdict: FAIL at 4f2c9a1d8b7e6c5a4f3e2d1c0b9a8f7e6d5c4b3a

Independent review of PR #54 (`ord-02/local-order-times`, closes #52): the formatting and tests pass, but one zone
shows no zone name.

## Blocking — no zone name for a zone without an abbreviation
`web/src/pages/Orders.tsx:88` takes only the short abbreviation. With `TZ=Asia/Kathmandu` the cell shows `15:15`;
the issue requires the time and the zone name.

**Smallest fix:** fall back to the UTC offset when there is no abbreviation, with a test for that zone.

## Verified
1. **Scope & Diff:** `git diff origin/main...HEAD --stat` touches only the three owned files.
2. **Tests:** the page tests fail without the change.

## Security
- **Scan:** `security_scan.py --base origin/main --head 4f2c9a1d8b7e6c5a4f3e2d1c0b9a8f7e6d5c4b3a`: exit 0, no item
- **Outbound data:** none added or widened
- **Risk:** no proven finding
- **Not checked:** none

## Gate
```text
cd web && npm run check
  42 tests passed
```

## Residual
- none

Created: Reviewer (example)
