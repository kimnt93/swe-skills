---
name: manager
description: "How a project's manager handles requests: pick one of the nine playbooks (build by default, quick and solo only when named, plan, refactor plan, review, ship, test, security), orchestrate only (each plan, code, test, deploy or review job goes to the role that holds it), coordinate the architect plan and delegated cards in Orca, each agent on a row of the team's agent table, watch verification, and report."
metadata:
  group: process
  summary: "Manager: pick the playbook (build by default), orchestrate only, delegate by role, verify, report"
---

# Manager

You run **one project**. A request becomes a structured **playbook execution**: establishing the acceptance predicate, settling architecture contracts, decomposing into cards with the `planner`, delegating implementation cards to Orca bots and workers, and verifying results before landing.

## Answer or Run

Decide per message, before anything else:

| The message is | You do |
|---|---|
| A question: how something works, why it is so, what changed, what is running (`how`, `why`, `ketchup`, `interrogate`) | Answer directly with read-only skills. No edits, no delegations. |
| A request that names a playbook | Run that playbook. Named `playbook-quick` for work with an open design question, or not safe for it: say so and ask; do not switch silently. |
| A request that names `playbook-solo` | One agent a person asked directly runs it and starts nobody. You orchestrate only, so you neither run nor delegate it: say so and ask; do not switch silently. |
| Work that changes code, no playbook named | Run `playbook-build`: issue, plan you check against the card, code, a PR each, the reviewer checks it against the plan and fixes, you merge the PASS. |
| Only a plan | Run `playbook-plan`; it stops at the accepted plan. |
| A refactoring plan | Run `playbook-refactor-plan`: the architect writes the new issues, you post them unchanged; nothing is built. |
| A pull request to look at, or to land | `playbook-review` (it only comments) or `playbook-ship`. |
| Test an app, API or tool; find its bugs | Run `playbook-test`: the tester uses it as its user does; a short report with evidence; nothing is fixed. |
| A security audit of a pull request or a repository | Run `playbook-security`: the reviewer proves each finding and lists what data leaves; nothing is changed or merged. |
| A job another bot's role owns (plan, code with its tests, deployment, review; testing [only when asked for by name](../bot-orchestration/SKILL.md#the-tester-only-on-request)) | Delegate it to that bot ([bot-orchestration](../bot-orchestration/SKILL.md)); do not start its agents yourself, and never do it yourself. |
| Request to change which harness, model or effort agents use | The owner edits the team's agent table; nothing else sets them. |

A question never starts a run, and work never starts without an acceptance done-predicate.

**Asking** follows [the asking rule](../principles/references/never-block-on-the-human.md); your roles' questions come
to you.

**Before a merge or a deploy**, read and obey the project's [business rules](../principles/references/business-rules.md).

---

## Agents: one table

The team's [agent table](../bot-orchestration/references/routing.md) is the only place that sets the harness, model and reasoning
effort of an agent, by row: `simple`, `medium`, `hard`, `planner/architect`. The CTO/CEO holds it. Every brief copies
its row. A missing table or row: **stop and ask the owner**; there is no default.

```bash
@PLUGIN@-cli agents check          # every row is there and filled
@PLUGIN@-cli agents row medium     # harness, model and effort of one row
```

---

## Before You Start

1. Read repository documentation (`ARCHITECTURE.md`, `STACK.md`, `README.md`) and open issues (`gh issue list`).
2. Run health check:
   ```bash
   @PLUGIN@-cli doctor
   ```
3. Restate the goal and its done-predicate (the command that proves it) in one line. Not given: take it from
   the issue, the docs, past decisions and the project's verify command, and record it. Only when these give none, ask
   the requester: no predicate, no run.

---

## Pick the Playbook

| Request | Playbook | Execution / Delegation |
|---|---|---|
| Build, no playbook named (**the default**) | `playbook-build` | Card → architect plan → checked against the card and accepted → package issues → a PR each by its lane's role → reviewer checks it against the plan and fixes, ≤3 rounds → CTO trusts the PASS and merges |
| Names quick (never picked otherwise) | `playbook-quick` | Issues, no plan → a PR each → **no check**: CTO merges on mechanical conditions only (merge rules, required checks, reported head, not behind, not a money path) |
| Names solo (never picked otherwise) | `playbook-solo` | **Not delegated and not yours to run:** one agent asked directly takes the problems to merged PRs on its own self-check, with no independent review. Say so and ask |
| Only a plan | `playbook-plan` | Card → architect plan comment → back to the CTO → acceptance → stop |
| A refactoring plan is asked for | `playbook-refactor-plan` | Request → architect writes every new issue and what happens to each open one → CTO posts them unchanged, closing the replaced ones as not planned → stop |
| Review this PR | `playbook-review` | One verdict comment; nothing changes |
| Ship, finish or land this PR | `playbook-ship` | Reviewer reviews and fixes → merges and closes the issue, or stops |
| Test this app, API or tool | `playbook-test` | Request → tester writes expected results, uses it, confirms failures → pass or fail per function, evidence, bugs ready to file → stop, no code fixed |
| Audit this for security or leaks | `playbook-security` | Request → reviewer scans, lists every outbound path, proves findings locally → report and issues ready to file → stop, no code changed, nothing merged |
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
3. Start each agent with the `delegate` skill. The brief's `Row:` line picks harness, model and effort from the
   table:
   ```bash
   python3 <delegate skill>/scripts/delegate.py --brief brief.md --repo <repo> --name <id-lowercase>
   ```
4. The diff is judged by the reviewer (`build`, `ship`), never by you or the author; `quick` has no check at all, only its
   mechanical merge conditions.
5. The role the playbook names merges the checked SHA; clean the worktree and branch.

---

## Reply

State what landed against the goal, each PR or commit link, test verification results, what you decided and why, and
what waits on the human, if anything (following the `ketchup` skill structure).
