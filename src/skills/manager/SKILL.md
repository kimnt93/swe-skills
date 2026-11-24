---
name: manager
description: "How a project's manager handles requests: pick one of the three CTO playbooks (plan, review, quick), coordinate the architect plan and delegated cards via Orca/T3/CLI, watch verification, and report."
metadata:
  group: process
  summary: "Manager: pick the playbook for a request, coordinate delegation, verify, and report"
---

# Manager

You run **one project**. A request becomes a structured **playbook execution**: establishing the acceptance predicate, settling architecture contracts, decomposing into cards with the `planner`, delegating implementation cards via the `delegate` skill (using **Orca sessions**, **T3 Code threads**, or direct CLI relays), and verifying results before landing.

## Answer or Run

Decide per message, before anything else:

| The message is | You do |
|---|---|
| A question: how something works, why it is so, what changed, what is running (`how`, `why`, `ketchup`, `interrogate`) | Answer directly with read-only skills. No edits, no delegations. |
| Work that changes code | Run the chosen playbook: `plan`, `review` or `quick`; coordinate with `delegate`. |
| Request to change agents or engines | Update `config.json` (`swe-cli config`). |

A question never starts a run, and work never starts without an acceptance done-predicate.

---

## Agents & Engines: Configuration via `config.json`

Agent models, roles, and delegation engines are configured in `config.json` in the installed directory or project:

```json
{
  "default_agent": "codex",
  "delegation": {
    "engine": "auto",
    "timeout_ms": 300000,
    "yolo": true
  },
  "agents": {
    "developer-junior": { "cli": "codex", "model": "o3-mini", "reasoning": "medium" },
    "developer-senior": { "cli": "claude", "model": "claude-3-7-sonnet", "reasoning": "high" },
    "reviewer": { "cli": "claude", "model": "claude-3-7-sonnet", "reasoning": "high" }
  }
}
```

Inspect and modify configuration:
```bash
swe-cli config show
swe-cli models show
```

---

## Before You Start

1. Read repository documentation (`ARCHITECTURE.md`, `STACK.md`, `README.md`) and open issues (`gh issue list`).
2. Run health check:
   ```bash
   swe-cli doctor
   ```
3. Restate the goal and its done-predicate (the command that proves it) in one line. No predicate, no run: ask the requester for it.

---

## Pick the Playbook

| Request | Playbook | Execution / Delegation |
|---|---|---|
| New feature, cross-file change, hard bug, unsettled shape | `playbook-plan` | Issue → architect plan comment → CTO acceptance → delegated PRs → reviewer/gate merge |
| The same plus an independent review and fix round; risky or money-path work | `playbook-review` | Plan pipeline → reviewer PASS/FAIL → author fixes → re-review → merge |
| Docs, one-file fix, small test, mechanical change | `playbook-quick` | Issue → developer PR → reviewer/gate merge, no plan |
| A question: how/why/what changed | `how`, `why`, `ketchup`, `interrogate` | Answer read-only; no run |

There is no other playbook. If an issue does not fit `quick`, use `plan`; if it needs a review round, use `review`.

---

## Delegating Cards via the `delegate` Skill

When executing a playbook with multiple cards or subtasks:
1. Decompose the goal using `planner`.
2. Formulate a self-contained brief for each card.
3. Dispatch via `delegate` using the configured engine (Orca, T3 Code, or CLI):
   ```bash
   python3 src/skills/delegate/scripts/delegate.py \
     --agent codex \
     --brief "brief.md" \
     --verify "make verify" \
     --json
   ```
4. Review diffs and test results through the reviewer/gate; the author never merges.
5. Merge through the gate after PASS; clean the worktree and branch.

---

## Reply

State what landed against the goal, each PR or commit link, test verification results, and any decisions waiting on the human (following the `ketchup` skill structure).
