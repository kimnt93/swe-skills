---
name: manager
description: "How a project's manager handles requests: pick the playbook that fits (delivery, feature, bugfix, docs, ci-fix, rebase, review, land, verify), coordinate execution, delegate implementation cards via Orca, T3 Code, or CLI relays, watch verification, and report."
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
| Work that changes code and matches a playbook | Run the playbook: coordinate phases and delegate cards via `delegate`. |
| Solo request: user wants you to do it all in-chat | Follow `playbook-solo`. |
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
| Any code goal across repos (default) | `playbook-deliver` | Plan cards, delegate implementation, verify, review, land |
| A single feature card | `playbook-feature` | Test-first implementation and verification |
| A defect with a way to reproduce it | `playbook-bugfix` | Failing test first, minimal fix, zero regression |
| Check a PR, read-only | `playbook-review` | Adversarial review with command proof |
| Red required check on open PR | `playbook-cifix` | Minimal fix within card files to turn CI green |
| Documentation out of date or missing | `playbook-docs` | Sync docs/ with code changes, run every example |
| PR behind main or has conflicts | `playbook-rebase` | Scoped rebase within card files, re-verify |
| Take an approved PR to main | `playbook-land` | Run verify gate on head, squash merge |
| Nightly or periodic health check | `playbook-verify` | Drive feature map against live app |
| In-chat execution without delegating | `playbook-solo` | Run all steps directly in this session |

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
4. Review diffs and test results.
5. Land each card safely using `playbook-land`.

---

## Reply

State what landed against the goal, each PR or commit link, test verification results, and any decisions waiting on the human (following the `ketchup` skill structure).
