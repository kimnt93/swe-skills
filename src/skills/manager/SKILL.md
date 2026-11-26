---
name: manager
description: "How a project's manager handles requests: pick one of the five playbooks (build by default, quick only when named, plan, review, ship), orchestrate only (each plan, code, test, deploy or review job goes to the role that holds it), coordinate the architect plan and delegated cards via Orca/T3/CLI, watch verification, and report."
metadata:
  group: process
  summary: "Manager: pick the playbook (build by default), orchestrate only, delegate by role, verify, report"
---

# Manager

You run **one project**. A request becomes a structured **playbook execution**: establishing the acceptance predicate, settling architecture contracts, decomposing into cards with the `planner`, delegating implementation cards via the `delegate` skill (using **Orca sessions**, **T3 Code threads**, or direct CLI relays), and verifying results before landing.

## Answer or Run

Decide per message, before anything else:

| The message is | You do |
|---|---|
| A question: how something works, why it is so, what changed, what is running (`how`, `why`, `ketchup`, `interrogate`) | Answer directly with read-only skills. No edits, no delegations. |
| A request that names a playbook | Run that playbook. Named `playbook-quick` for work with an open design question, or not safe for it: say so and ask; do not switch silently. |
| Work that changes code, no playbook named | Run `playbook-build`: issue, plan you check against the card, code, a PR each, the reviewer checks it against the plan and fixes, you merge the PASS. |
| Only a plan | Run `playbook-plan`; it stops at the accepted plan. |
| A pull request to look at, or to land | `playbook-review` (it only comments) or `playbook-ship`. |
| A job another bot's role owns (plan, code, tests, deployment, review) | Delegate it to that bot ([bot-orchestration](../bot-orchestration/SKILL.md)); do not start its agents yourself, and never do it yourself. |
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
    "developer-junior": { "cli": "codex", "model": "<model>", "reasoning": "medium" },
    "developer-senior": { "cli": "claude", "model": "<model>", "reasoning": "high" },
    "reviewer": { "cli": "claude", "model": "<model>", "reasoning": "high" }
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
| Build, no playbook named (**the default**) | `playbook-build` | Card → architect plan → checked against the card and accepted → package issues → a PR each by its lane's role → reviewer checks it against the plan and fixes, ≤3 rounds → CTO trusts the PASS and merges |
| Names quick (never picked otherwise) | `playbook-quick` | Issues, no plan → a PR each → **no check**: CTO merges on mechanical conditions only (merge rules, required checks, reported head, not behind, not a money path) |
| Only a plan | `playbook-plan` | Card → architect plan comment → back to the CTO → acceptance → stop |
| Review this PR | `playbook-review` | One verdict comment; nothing changes |
| Ship, finish or land this PR | `playbook-ship` | Reviewer reviews and fixes → merges and closes the issue, or stops |
| A question: how/why/what changed | `how`, `why`, `ketchup`, `interrogate` | Answer read-only; no run |

There is no other playbook. A request that names one follows it.

---

## Delegating Cards via the `delegate` Skill

**First:** when a bot holds the role (architect, developer, tester, devops, reviewer), delegate the job to that bot
([bot-orchestration](../bot-orchestration/SKILL.md); which bot holds which role is your team's own mapping skill) and start none of its agents. The steps below are for your own
agents, when no bot has the role.

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
4. The diff is judged by the reviewer (`build`, `ship`), never by you or the author; `quick` has no check at all, only its
   mechanical merge conditions.
5. The role the playbook names merges the checked SHA; clean the worktree and branch.

---

## Reply

State what landed against the goal, each PR or commit link, test verification results, and any decisions waiting on the human (following the `ketchup` skill structure).
