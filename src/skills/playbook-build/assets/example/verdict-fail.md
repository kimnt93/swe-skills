Verdict: FAIL at 3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f. Round 1 of 3.

Checked PR #64 (`rate-00a/limit-per-key`, closes #61) at its head against the issue and plan v1 on #60: one departure
from the plan.

## Blocking — idle buckets are never dropped, which the plan requires
Plan v1 (`Risks & Gates`) says idle buckets are dropped after 10 minutes. `src/api/ratelimit.py` keeps one bucket per key
forever: after 50,000 distinct keys in the new memory test, `len(limiter.buckets)` is `50000` with every key idle for 11
minutes.

**Smallest fix:** drop a bucket on its next lookup once it has been idle for 10 minutes, with a test that moves the clock.

## Security
- **Scan:** `security_scan.py --base origin/main --head 3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f`: exit 0, no item
- **Outbound data:** none added or widened
- **Risk:** the finding under Blocking: callers with new keys grow memory without bound
- **Not checked:** none

## Gate
```text
make verify
  58 passed
```

## Residual
- I fix this next, on the same branch.

Created: Reviewer (example)
