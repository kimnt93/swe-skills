---
name: playbook-bugfix
description: "Bugfix playbook: reproduce defects with an automated failing test first, apply the smallest scoped fix, verify regression boundaries, and submit for review."
metadata:
  group: start
  summary: "Playbook for bugfixes: reproduce with failing test, smallest fix, verify, and review"
---

# Playbook: Bugfix

The bugfix playbook resolves defects safely by requiring a reproducible failing test before any production code is altered.

## Steps

### 1. Defect Reproduction
1. Extract the minimal reproduction steps from the reported issue or symptom.
2. Write a focused unit or integration test that reliably fails on the current codebase.
3. Confirm that the test fails exclusively because of the targeted bug, not ambient setup issues.

### 2. Root Cause Analysis
1. Inspect commit history and context using `why` to understand why the existing logic was written that way.
2. Identify boundary conditions, concurrency races, or unhandled input values.

### 3. Minimal Scoped Fix
1. Apply the smallest possible change that makes the failing test pass using `developer` or `delegate`:
   ```bash
   python3 src/skills/delegate/scripts/delegate.py \
     --agent codex \
     --brief "brief.md" \
     --verify "pytest -k test_bug"
   ```
2. Refrain from refactoring unrelated modules or expanding scope during a bugfix.

### 4. Regression & Verification Gate
1. Run the entire test suite and verify command (`make verify`) to confirm zero regressions.
2. Check potential collateral breakage using `blast-radius`.
3. If this defect was a repeated mistake, formalize prevention using `correct`.

### 5. Review & Submission
1. Review the diff with `reviewer` to ensure the fix is minimal and robust.
2. Open pull request linking the issue and documenting the reproduction test.
