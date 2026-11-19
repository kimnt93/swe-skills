---
name: playbook-feature
description: "Feature development playbook: implement a new feature card or specification with interface contracts, test-first development, delegated implementation via Orca, T3 Code, or CLI relays, verification, and PR review."
metadata:
  group: start
  summary: "Playbook for feature implementation: specification, planning, delegation, and test verification"
---

# Playbook: Feature

The feature playbook guides the implementation of a single feature or capability within a codebase, ensuring solid architecture, test coverage, and clean review.

## Steps

### 1. Specification & Grounding
1. State the user-observable outcome and the test command that demonstrates it.
2. Read existing patterns in the codebase using `how`.
3. Check `config.json` for agent assignments and engine preferences.

### 2. Architecture & Design
1. Settle types, signatures, and module shapes before modifying code using `architect`.
2. Evaluate potential side effects across other components using `blast-radius`.

### 3. Test-First Implementation
1. Write the failing unit or integration test first using `tdd`.
2. Dispatch implementation via the `delegate` skill:
   ```bash
   python3 src/skills/delegate/scripts/delegate.py \
     --agent codex \
     --brief "brief.md" \
     --verify "make verify"
   ```
3. Implement the minimal clean code necessary to turn the test green.

### 4. Verification & Cleanliness
1. Run full project verification (`make verify`).
2. Remove dead code, redundant comments, and debug prints using `deslop`.
3. Update relevant documentation in `docs/` using `docs-sync`.

### 5. Review & Pull Request
1. Conduct adversarial review using `interrogate`.
2. Open pull request with structured summary and test evidence using `github`.
