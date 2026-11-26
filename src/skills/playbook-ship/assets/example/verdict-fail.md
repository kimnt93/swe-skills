Verdict: FAIL at 4f2c9a1d8b7e6c5a4f3e2d1c0b9a8f7e6d5c4b3a. Round 1 of 3.

Checked PR #54 (`ord-02/local-order-times`, closes #52) at its head: one case does not meet the issue.

## Blocking — no zone name for a zone without an abbreviation
With `TZ=Asia/Kathmandu` the page test shows `15:15`; the issue requires the time and the zone name.

**Smallest fix:** fall back to the UTC offset when there is no abbreviation, with a test for that zone.

## Gate
```text
cd web && npm run check
  42 tests passed
```

## Residual
- I fix this next, on the same branch.

Created: Reviewer (example)
