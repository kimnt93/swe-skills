Accepted by CTO (example). PR #54 at 9b8a7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b.

Checked PR #54 again at the new head: the missing zone name is fixed.

## Verified
1. **Scope & Diff:** `gh pr diff 54` touches only the three owned files; `pr_lint.py pr 54` reports 0 problems.
2. **Zone name:** with `TZ=Asia/Kathmandu` the cell shows `15:15 GMT+5:45`.

## Gate
```text
cd web && npm run check
  43 tests passed
gh pr checks 54
  all required checks passed
```

## Residual
- none

Created: CTO (example)
