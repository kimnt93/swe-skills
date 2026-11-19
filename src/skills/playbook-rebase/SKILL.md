---
name: playbook-rebase
description: "Rebase playbook: bring an open pull request up to date with the latest main branch, resolve merge conflicts safely within card-owned files, re-verify gates, and submit for review."
metadata:
  group: start
  summary: "Playbook for branch rebase: safe conflict resolution within scoped files and re-verify"
---

# Playbook: Rebase

The rebase playbook updates an open PR branch against `main` and resolves merge conflicts cleanly without overwriting changes from other cards.

## Steps

### 1. Fetch & Rebase
1. Fetch latest changes from the primary upstream branch:
   ```bash
   git fetch origin main
   git checkout feature-branch
   git rebase origin/main
   ```

### 2. Scoped Conflict Resolution
1. Follow `integrator` rules: resolve conflicts strictly within files owned by this PR's card.
2. If conflicts touch files outside the PR's designated scope or shared hotspot files, halt and escalate.
3. Keep the intent of upstream commits intact while integrating your changes.

### 3. Re-run Verification Gate
1. After resolving conflicts and completing the rebase:
   ```bash
   make verify
   ```
2. Verify that unit tests, lint checks, and typechecks pass with zero failures.

### 4. Push & Fresh Review
1. Force-push with lease:
   ```bash
   git push --force-with-lease origin feature-branch
   ```
2. Request a fresh review round with `reviewer` to certify the rebased head commit.
