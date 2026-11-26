Returned by CTO (example). PR #54 at 4f2c9a1d8b7e6c5a4f3e2d1c0b9a8f7e6d5c4b3a. Rebase after #55.

Sent back to the developer for a mechanical reason; nobody judged the code. This return is free: PR #55, another quick
PR of this run, merged after #54's report, and #54 only needs a clean rebase on the new `main`.

## Blocking — PR #54 is behind `main` after #55 merged
`gh pr view 54 --json mergeStateStatus` shows `BEHIND`.

**Smallest fix:** the developer rebases on `main` in the same worktree, runs the `Done when` on the new head and
reports it.

## Gate
```text
gh pr view 54 --json mergeStateStatus
  {"mergeStateStatus": "BEHIND"}
```

## Residual
- returns used: 0 of 3; this rebase does not count.

Created: CTO (example)
