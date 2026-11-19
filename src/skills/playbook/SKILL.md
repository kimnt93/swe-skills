---
name: playbook
description: "Dispatcher for engineering playbooks. Lists available playbooks and guides orchestrators and agents through structured workflows for delivery, features, bugfixes, reviews, CI fixes, documentation, rebasing, and landing."
metadata:
  group: start
  summary: "List and dispatch engineering playbooks for delivery, features, bugfixes, reviews, and landing"
---

# Playbook

Playbooks define repeatable, structured procedures for software engineering tasks. They organize work into explicit phases (Intake, Architecture, Planning, Execution, Verification, Review, and Landing) and coordinate delegation via **Orca sessions**, **T3 Code threads**, or direct CLI relays using the `delegate` skill.

## Available Playbooks

| Playbook | Purpose | Delegation / Execution |
|---|---|---|
| **playbook-deliver** | Complete end-to-end delivery: goal to merged PR and verified code | Multi-agent delegation (Orca / T3 / CLI) |
| **playbook-feature** | Feature development from specification to verified implementation | Multi-agent delegation |
| **playbook-bugfix** | Defect reproduction with failing test, minimal fix, and verification | Delegated or direct |
| **playbook-review** | Read-only adversarial review of a PR or diff with command proof | Read-only reviewer |
| **playbook-cifix** | Investigation and fix for failing CI check on an open PR | Delegated or direct |
| **playbook-docs** | Documentation authoring or synchronization with code changes | Documenter / scribe |
| **playbook-rebase** | Bring PR branch up to date with main and safely resolve conflicts | Integrator |
| **playbook-land** | Execute verify gate and squash merge approved PR | Orchestrator gate |
| **playbook-changelog** | Audit and update CHANGELOG.md for merged PRs and releases | Scribe |
| **playbook-verify** | Drive live application verification against feature map | Verifier |
| **playbook-solo** | Execute task end-to-end in active chat without delegation | In-chat solo |

## How to Run a Playbook

1. **Select the matching playbook** from the table above.
2. **Review configuration** in `config.json` (or defaults) for target agents, models, and execution engine (Orca, T3 Code, or CLI).
3. **Follow the playbook phases**:
   - Establish done-predicate (command that proves completion).
   - Use `architect` and `planner` for multi-file changes.
   - Dispatch implementation units via the `delegate` skill (`/delegate` or `python3 src/skills/delegate/scripts/delegate.py`).
   - Run verification and adversarial reviews before landing.
