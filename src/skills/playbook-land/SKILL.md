---
name: playbook-land
description: "Landing playbook: take an approved pull request across the finish line to main. Proves the verify gate on the committed head, ensures documentation and changelog are present, and executes squash merge."
metadata:
  group: start
  summary: "Playbook for landing PRs: execute verify gate, squash merge, and branch cleanup"
---

# Playbook: Land

The landing playbook executes the final merge gate on an approved pull request and lands it safely into `main`.

## Steps

### 1. Pre-Merge Verification
1. Ensure the PR branch is fully up to date with `main`. If behind or conflicting, run `playbook-rebase` first.
2. Verify all required CI checks are green:
   ```bash
   gh pr checks <pr-number>
   ```
3. Run project verification locally on the exact head commit:
   ```bash
   make verify
   ```

### 2. Documentation & Changelog Audit
1. Confirm that documentation changes have been made if the PR alters public interfaces or behavior.
2. Confirm that a changelog entry exists in `CHANGELOG.md` using `changelog`.

### 3. Merge Gate Execution
1. Execute squash merge using `github`:
   ```bash
   gh pr merge <pr-number> --squash --auto --delete-branch
   ```

### 4. Post-Merge Verification & Cleanup
1. Pull the updated `main` branch locally:
   ```bash
   git checkout main && git pull origin main
   ```
2. Verify that `main` builds and tests pass cleanly.
3. Remove local worktrees or transient branches.
