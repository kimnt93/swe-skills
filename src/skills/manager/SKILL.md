---
name: manager
description: "How a project's manager handles requests: pick one of the five playbooks (plan, quick, complete, review, ship), coordinate the architect plan and delegated cards via Orca/T3/CLI, watch verification, and report."
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
| A problem to plan or design | Run `playbook-plan`; it stops at the accepted plan. |
| Work that changes code | Run the chosen playbook: `quick`, `complete` or `ship`; coordinate with `delegate`. |
| A pull request to look at | Run `playbook-review`; it only comments. |
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
| Plan a new feature, cross-file change, hard bug, unsettled shape | `playbook-plan` | Card → architect plan comment → back to the CTO → acceptance → stop |
| Ready to build, `simple` or `medium`, checked by the CTO | `playbook-quick` | Issues → a PR each → ≤3 feedback rounds → CTO merges or stops |
| Features, hard work, an accepted plan, with a separate reviewer | `playbook-complete` | Issues → a PR each → reviewer reviews and fixes → CTO trusts the PASS and merges |
| Review this PR | `playbook-review` | One verdict comment; nothing changes |
| Ship, finish or land this PR | `playbook-ship` | Reviewer reviews and fixes → merges and closes the issue, or stops |
| A question: how/why/what changed | `how`, `why`, `ketchup`, `interrogate` | Answer read-only; no run |

There is no other playbook. An open design question goes to `plan` first.

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
4. Judge the diff as the playbook says (`quick`: the CTO/CEO; `complete` and `ship`: the reviewer); the author never merges.
5. The role the playbook names merges the checked SHA; clean the worktree and branch.

---

## Reply

State what landed against the goal, each PR or commit link, test verification results, and any decisions waiting on the human (following the `ketchup` skill structure).
