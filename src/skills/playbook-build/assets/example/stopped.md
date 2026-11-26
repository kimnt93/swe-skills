Stopped by reviewer (example). PR #64 at 7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e.

Checked PR #64 after round 3 of 3: one case still does not meet the issue, so the loop ends here.

## Blocking — a burst after a quiet minute is refused
With `RATE_LIMIT_BURST=100`, a key idle for a minute that sends 100 requests at once gets `429` on the 61st; the plan
requires the burst on top of the per-minute rate.

**Smallest fix:** refill the bucket to the burst size, not to the per-minute rate, with a test for a burst after a quiet
minute.

## Gate
```text
make verify
  1 failed, 59 passed
```

## Residual
- A person decides: continue under a new plan, or replace the issue. This PR stays open and its branch stays on GitHub.

Created: Reviewer (example)
