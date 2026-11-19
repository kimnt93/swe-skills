---
name: playbook-solo
description: "Solo playbook: execute a task end-to-end within this chat conversation without delegating or launching subagents. Covers intake, architecture, coding, verification, and landing."
metadata:
  group: start
  summary: "Playbook for solo execution: plan, code, verify, and land in this chat without delegation"
---

# Playbook: Solo

The solo playbook executes a complete task directly within the current chat session without delegating to external agent processes or launching subagents.

## Inputs
- **Goal**: An issue (`#42`), user request, or sentence with an acceptance command.
- **Mode**: `full` (complete through commit and PR) or `plan` (stop after architecture and planning).

## Steps

### 1. Grounding & Understanding
1. State the goal and the acceptance command that proves completion.
2. Read relevant architecture and conventions (`ARCHITECTURE.md`, `STACK.md`).
3. Map affected modules using `how`.

### 2. Architecture & Design
1. For code crossing a function or module boundary, design types and signatures first using `architect`.
2. Check blast radius with `blast-radius`.

### 3. Test-First Implementation
1. Write the failing test first using `tdd`.
2. Implement the smallest scoped change to satisfy the test.
3. For money-path code, add replay tests with `replay-test`.

### 4. Verification & Cleanliness
1. Run `make verify` and confirm zero failures.
2. Clean unnecessary debug code with `deslop`.
3. Update documentation with `docs-sync`.

### 5. Land
1. Commit changes using Conventional Commits with `github`.
2. Open pull request with test proof.

## Boundaries
- Do not launch subagents or delegate sessions when running in solo mode.
