---
name: bot-orchestration
description: "How standing bots and the agents they start work together: who may message whom (bot to agent, agent back to its own bot, bot to bot to delegate and to report), never agent to agent. The CEO or CTO bot only orchestrates: it writes the issue and delegates it to the bot of its role (architect, developer, tester, devops, reviewer); the developer bot rates it simple, medium or hard, starts an agent on that row of the team's agent table, which builds it and opens the PR, then verifies the work and reports back. Use before delegating a job to another bot, before starting any agent as a bot, and when reporting back."
metadata:
  group: process
  summary: "Bots delegate to bots and run their own agents; agents report only to their bot"
---

# Bot orchestration

| | **Bot** | **Agent** |
|---|---|---|
| What it is | a standing member with a name, a role, memory and chats | a sub-process of any coding CLI that a bot starts for one job |
| Lives | across jobs | until its job is done |
| Orchestrates | yes: its own agents, and delegates to other bots | **no** |
| Talks to | other bots, and the agents it started | **only the bot that started it** |

**The bot is the orchestrator. Agents do separate work and never talk to each other.**

**A bot never does the task itself.** Code, tests, deployment work, a review and its fixes, a plan's analysis: each goes
to the bot that holds the role, or to the bot's own agent on the right [row](references/routing.md). The bot's own work is
to decide, delegate, **verify** (run the evidence command, read the result) and report; where its playbook gives it the
issue, the decision comment or the merge, it does those itself.

```text
CEO bot ── issue ──► developer bot ──┬─ brief ─► agent A (issue 1, own worktree)
   ▲                  ▲     │        └─ brief ─► agent B (issue 2, own worktree)
   │                  └─────┼───────────── report ─┘   (each agent only to its bot)
   │                        │ verify, PR
   └────── status ──────────┘
```

## The messages

| From → to | Use it to | Orca | Template |
|---|---|---|---|
| bot → bot | **delegate** a job | `send --to "bot:<name>" --chat new --type handoff` the first time, then `send --to "bot:<name>" --chat <child chat id> --type handoff` | [delegate](assets/delegate.template.md) |
| bot → its agent | **brief** it, then steer it | `worker-start`, then `send --to dispatch:<id>` | [agent brief](assets/agent-brief.template.md) |
| agent → its bot | **report** the result, or ask | `worker_done`, `ask`, `escalation` | [agent report](assets/agent-report.template.md) |
| bot → bot | **status** when done or blocked | `send --to "bot:<name>" --chat <return chat id> --type status` | [bot report](assets/bot-report.template.md) |
| bot → bot | **follow up** on a delegated job: changes, merged, stopped | `send --to "bot:<name>" --chat <child chat id> --type handoff` | [follow-up](assets/follow-up.template.md) |

A message to **your own** agent after its brief (`send --to dispatch:<id>`) is free text: it comes from its bot.
An agent is never given a bot's handoff: it gets an agent brief.

A short question between bots, with no job handed over, uses `--type question`, in the child chat. Every other route is **forbidden**:
agent → agent, agent → another bot, agent → a bot that did not start it, and a bot steering another bot's agent.

Check each message before you send it; the linter reads the template, so editing a template changes the rule:

```bash
python3 <this skill>/scripts/message_lint.py <delegate|agent-brief|agent-report|bot-report|follow-up> --body-file msg.md
```

Commands: [commands](references/commands.md). A full run: [example](references/example.md).

## One child chat per parent chat and bot

The **parent chat** is the chat you delegate from. Each bot you delegate to from it has **one child chat** for it.

- **First delegation** from a parent chat to a bot: `--chat new`, with the **parent chat's name as the subject**. Orca
  titles the new chat `<sender bot name>: <subject>`; the title is fixed then.
- **Record the child chat's id**, by parent chat and receiving bot, where a resumed run can read it
  ([how](references/commands.md#the-child-chat)).
- **Every later message** from that parent chat to that bot (the next job, a follow-up, changes, merged, stopped, a
  question) uses `--chat` with that id. **Never send delegated work to a bot with no `--chat`:** it lands in the
  receiver's Home Chat.
- **A different parent chat gets its own child chat.** A bot that delegates further does the same from its own chat and
  keeps the same subject (its chat's title without the sender's name), so the chain is easy to follow.
- **The child chat is gone, unknown, or more than one matches:** open a new one with `--chat new`, record the new id and
  put the context the receiver needs in that message. **Never guess a chat.**
- A status still goes to the parent's return address.

**Good:** from its chat `example start`, the CTO bot opens a chat on the developer bot with that subject; it shows as
`<CTO bot>: example start`. The next issue, the change request and `MERGED` go to its recorded id, and the developer
bot delegates onward from there with the subject `example start`.
**Bad:** the CTO bot sends the change request to the developer bot's name alone. It lands in the Home Chat, which knows
nothing about the job.

## One agent table

The CTO/CEO holds the team's [agent table](assets/agent-table.template.md): the rows `simple`, `medium`, `hard` and
`planner/architect`, each with a harness, a model and a reasoning effort. It is the only place that sets them. Every
brief copies its row, every handoff tells the receiving bot to start its agents from the table, and a missing row means
**stop and ask**. [Which row](references/routing.md).

## Short replies

A reply or a status report is short: the result, the evidence, the head and what is left, and nothing the reader does
not need to act. Long explanation belongs only in the planner/architect's plans and issues, or where somebody asked for
it.

- **Good:** `PR READY API-03: head <sha>; make verify passed; nothing left.`
- **Bad:** a status that retells the whole run: every file read, every dead end, then the result in the last line.

## Delegate a bot's job to that bot

**Roles, not names.** The skills of this plugin name roles only, never a bot. Which bot holds which role is each team's
own mapping skill, kept outside this repository: the orchestrating bot reads it first, and only without one reads the
bot list.

**Look first** (the team's mapping skill, else `ORCA bot list`). When a bot has the role, hand it the job. **Do not start that role's agents yourself.**
A bot starts agents for **its own** job only. Only when no bot has the role may the delegating bot start the agent.

| Role bot | Owns | Does not |
|---|---|---|
| **CEO / CTO** | **only orchestrates**: writes the issues, runs the playbook (delegating, the plan decision, the merge its playbook gives it), reports to the owner | plan, code, test, deploy or review code itself, in any playbook; start an agent for a role another bot holds |
| **Architect** | the plan: analysis, the plan comment, sending it back | accept its own plan, build |
| **Developer** | the code job: difficulty, agents, worktrees, verification, the PR, the report | write the code itself, design or priority calls, review of its own PR, the merge |
| **Tester** | a `test` lane issue: tests and verification work, built and reported like the developer's; a [playbook-test](../playbook-test/SKILL.md) run: test as a user, report, fix nothing | judge a PR as its reviewer, the merge |
| **Devops** | an `ops` lane issue: deployment, CI and infrastructure work, built and reported like the developer's | deploy or touch production without the owner's go, the merge |
| **Reviewer** | the verdict on a PR it did not write, drafted by its own agents, with its [security and outbound-data check](../reviewer/SKILL.md#security-and-outbound-data); in `build` and `ship` also the fixes and the check against the accepted plan, and in `ship` the merge; a [playbook-security](../playbook-security/SKILL.md) audit: proven findings, change nothing | build the PR it judges; take part in `quick`, which has no check |

Each role is the same rule: the bot that holds it does the job through its own agents. With no tester or devops bot, the
developer bot builds that issue; with no bot for a role at all, the CEO/CTO starts its own agent for it, named
`<bot name> / <role>`.

**"Ended its turn without a reply"** is not proof that a bot did nothing: Orca can say it right after the bot reported,
because a `status` is not a reply to the handoff. **Look for its status first** (your chat,
`ORCA orchestration inbox`). It arrived: that is the report, so verify it and continue. None arrived (for example the
bot is out of quota): the job is still **that bot's**. Do not redo it, call it dropped, or start its role's agents. Tell
the owner which bot, which job and why, and let them decide.

An analysis, a check or a search that is part of a bot's own job may use its own agent: a CEO may start one to read the
state of its issues, not to build them.

## The build flow

1. **CEO bot** writes the issue (`write-issue`), checks the [merge rules](../github/references/pull-requests.md#merge-rules) allow it,
   **delegates** it to the developer bot with its own return address, and **ends its turn**.
2. **Developer bot** (the tester bot for a `test` lane issue, the devops bot for an `ops` one) runs the gate, [rates the issue and reads that row of the agent table](references/routing.md), creates the issue's
   worktree, and **briefs one agent** per issue. Independent issues run in parallel, each with its own agent.
3. **Agent** does its slice, pushes it and opens the PR when its brief says so, and **reports to its bot only**.
4. **Developer bot verifies**: runs the evidence command itself and reads the diff against the owned files. A claim is
   not proof. It also checks that the PR is open and its checks are green.
5. **Developer bot** sends the CEO bot a **status** and ends its turn.
6. **CEO bot** continues its playbook: `playbook-build` (the default: it delegates the review to the reviewer bot,
   which checks the code against the accepted plan and fixes, and merges on its PASS) or `playbook-quick` (no check:
   it merges when the mechanical conditions hold, or sends a red check or a stale branch back to the developer bot).
   Feedback goes bot to bot; the developer bot gives it to the same agent, or a new one.

## Agents separate their work

- **One agent, one slice, one worktree at a time.** Two agents never write in the same worktree or own the same file.
- One issue normally takes one agent. Split it only into slices that run **one after another** in that worktree, or that
  are really separate issues.
- An agent starts **no helpers**, even where its launch text offers it: say so in the brief.
- What one agent needs from another goes **through the bot**: the bot reads the first report and writes it into the
  second brief.

## Names

The brief gives the agent its name; commits are authored by it and texts end `Created: <name>`. The PR says which row of the agent
table did the work.

| The bot that starts the agent | The agent's name |
|---|---|
| holds the role (the developer bot starts a developer agent) | **the bot's name** |
| does not, because no bot has the role (a CTO starts a developer or reviewer agent) | `<bot name> / <role>`, such as `CTO (example) / developer` |

So whoever judges a PR never has the writer's name: a CTO can accept its own developer agent's PR, and its reviewer agent
is a different writer from its developer agent.

## Done

- The delegating bot received one status with the result and its evidence.
- Every agent of the job has settled and is released; its worktree is removed when the playbook says so.
- No message went between two agents, or from an agent to anyone but its bot.

## One good, one bad

- **Good:** the CEO hands issue `API-03` to the developer bot and ends its turn; the developer bot starts an agent on the
  `medium` row, reruns its test, opens the PR and sends `PR READY`.
- **Bad:** the CEO starts five developer agents itself, nudges each one and collects their reports, while the developer
  bot sits idle; or it reads the diff and runs the tests to judge a PR, which is the reviewer's job.

## Never

- Start another role bot's agents, or take over its job, while that bot exists.
- Do a task yourself: plan, write the code or tests, deploy, fix a finding or do the review reading in the bot's own chat.
- Let an agent message another agent or another bot, or start its own helpers.
- Report an agent's claim you did not verify, or let an agent a bot started decide, accept or merge.
- Poll a healthy agent or bot: end your turn; Orca wakes you.
