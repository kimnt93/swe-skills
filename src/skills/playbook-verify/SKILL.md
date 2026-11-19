---
name: playbook-verify
description: "Verification playbook: drive nightly, post-merge, or periodic health checks against the real application. Replays the feature map, checks for regressions, and logs findings."
metadata:
  group: start
  summary: "Playbook for system verification: drive live tests against feature map and report drift"
---

# Playbook: Verify

The verification playbook proactively proves that the live application continues to work as expected by executing real user workflows against the feature map.

## Steps

### 1. Environment & Setup
1. Ensure the workspace is clean and on the latest `main` commit.
2. Confirm dependencies and local services are running.

### 2. Execute Verification Lever
1. Run the project's standard verification suite:
   ```bash
   make verify
   ```
2. Verify exit code is 0 and all static audits pass.

### 3. Drive Feature Map Workflows
1. Follow `verifier` guidelines: replay key end-to-end features defined in the project map or test suite.
2. Check API health endpoints, database connectivity, and UI rendering where applicable.

### 4. Record Regressions & Drift
1. If a test or contract breaks, file a reproducible defect issue using `github`.
2. Document any behavioral drift or performance degradation in the verification log.
