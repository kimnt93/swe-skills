Stopped by reviewer (example). PR #54 at 7c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d.

Checked PR #54 after round 3 of 3: one case still does not meet the issue, so the loop ends here.

## Blocking — the zone name is wrong across a daylight saving change
With `TZ=Australia/Lord_Howe` the page test shows the summer offset for a winter date; the issue requires the zone in
force at the order's time.

**Smallest fix:** take the zone name from `created_at`, not from the current date, with a test on both sides of the change.

## Gate
```text
cd web && npm run check
  1 failed, 43 tests passed
```

## Residual
- A person decides: continue under a new plan, or replace the issue. This PR stays open and its branch stays on GitHub.

Created: Reviewer (example)
