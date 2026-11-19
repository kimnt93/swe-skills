---
name: playbook-review
description: "Review playbook: judge a pull request or diff at its head commit, read-only. Runs adversarial challenge, filters to findings proven by a command or trace, and reports a clear PASS or FAIL verdict."
metadata:
  group: start
  summary: "Playbook for code review: read-only adversarial evaluation, test proof, and verdict"
---

# Playbook: Review

The review playbook performs a thorough, read-only adversarial evaluation of a pull request or code diff before merge.

## Steps

### 1. Checkout & Grounding
1. Fetch the target branch and inspect the full commit range:
   ```bash
   git fetch origin
   git diff main...HEAD --stat
   ```
2. Read the PR description, linked issue, and acceptance criteria.
3. Review architectural constraints from `ARCHITECTURE.md`.

### 2. Verification Gate Execution
1. Run the project verification command at the PR head:
   ```bash
   make verify
   ```
2. If verification fails, immediately report FAIL with the exact failure output.

### 3. Adversarial Analysis
1. Use `reviewer` and `interrogate` to actively search for flaws:
   - Concurrency races and missing locks
   - Unhandled nil/null states or missing error checks
   - Contract breaks in APIs, database migrations, or serialization
   - Unchecked boundary conditions
2. Discard theoretical or stylistic nitpicks: keep only findings that can be proven by a running command or concrete execution trace.

### 4. Verdict & Feedback
1. Post a structured review verdict:
   - **PASS**: All tests pass, architecture respected, zero proven defect findings.
   - **FAIL**: Concrete failing test or command output demonstrating the bug.
2. If findings exist, specify the exact file, line, and proof command so the author can address them quickly.
