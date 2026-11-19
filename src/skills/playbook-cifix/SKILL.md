---
name: playbook-cifix
description: "CI fix playbook: investigate and resolve a red required CI check on an open pull request, reproduce the failure locally, apply the minimal fix within the card's files, and verify green."
metadata:
  group: start
  summary: "Playbook for CI fix: reproduce red check, apply minimal scoped fix, and verify green"
---

# Playbook: CI Fix

The CI fix playbook resolves failing automated checks on an open pull request without destabilizing surrounding code.

## Steps

### 1. Identify Failing Check & Reproduce
1. Inspect CI logs using `gh pr checks` or the check run URL to find the exact failing step and log trace.
2. Reproduce the failure locally on the card's branch using the identical environment or test command:
   ```bash
   make test
   ```
3. Confirm that the reproduced failure matches the remote CI log.

### 2. Isolate Cause & Scope
1. Follow `ci-fixer` guidelines: stay strictly within the files owned by the card.
2. Never weaken tests, suppress linters without rationale, or alter shared infrastructure outside the PR scope.

### 3. Apply Scoped Fix
1. Make the smallest necessary code correction to satisfy the check.
2. Alternatively, delegate the fix to a worker agent using `delegate`:
   ```bash
   python3 src/skills/delegate/scripts/delegate.py \
     --agent codex \
     --brief "brief.md" \
     --verify "make verify"
   ```

### 4. Local Verification & Push
1. Run `make verify` on the committed head commit to ensure all gates pass locally.
2. Push the fix to the PR branch and monitor CI until the required checks turn green.
