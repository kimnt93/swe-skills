Fixed in 5a6b7c8d:
- idle buckets: dropped on lookup after 10 minutes idle, as plan v1 says; a test moves the clock past the limit

New head: 5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b. Please re-review.

## Gate
```text
make verify
  59 passed
```

## Residual
- I review the whole new head next.

Created: Reviewer (example)
