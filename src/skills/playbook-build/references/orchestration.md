# Orchestration

How the messages of `playbook-build` travel in Orca. Load the Orca `/orchestration` skill first. `ORCA`, the message
types and the commands for looking at a worker are as in
[the plan orchestration](../../playbook-plan/references/orchestration.md); the installed guide and `ORCA <command> --help`
win. Write each body to a file and pass `--body-file` or `--spec-file`.

## 1. Look before you send

Which bot holds which role is your team's own mapping skill, kept outside this plugin; read it first. Without one, read
the bot list:

```bash
ORCA bot list                                # which bots hold architect, developer, tester, devops, reviewer
ORCA bot chats                               # your own chats; "(this chat)" is the return chat
ORCA worktree ps --since 2h                  # is somebody already on these files?
```

| The job | Goes to the role | Only when no bot holds that role |
|---|---|---|
| the plan (stage 2) | architect | your own agent, named `<your name> / architect` |
| a `test` lane issue | tester | the developer |
| an `ops` lane issue | devops | the developer |
| any other issue | developer | your own agent, named `<your name> / developer` |
| the review and its fixes (stage 4) | reviewer | your own agent that wrote none of the PR, named `<your name> / reviewer` |

One job has one bot. If somebody is on it, send to that chat or worker.

## 2. Stages 1 and 2: the card and the plan

As [the plan orchestration](../../playbook-plan/references/orchestration.md), sections 2 to 4: a `handoff` to the
architect, its `status` back (`PLAN READY` or `PLAN BLOCKED`), a follow-up for changes. Then the CTO/CEO checks the plan,
posts the decision comment and, once it is `Accepted by`, goes on to section 3 instead of stopping.

## 3. Send each package to its builder

Once `issue_gate.py issue <n>` allows the issue, one `handoff` per issue, each in a chat of its own, in the
[delegate](../../bot-orchestration/assets/delegate.template.md) format:

```bash
ORCA orchestration send --to "bot:<developer>" --chat new --type handoff \
    --subject "BUILD <ID>: <outcome>" --body-file developer-brief.md
ORCA orchestration send --to "bot:<devops>" --chat new --type handoff \
    --subject "BUILD <ID>: <outcome>" --body-file devops-brief.md
ORCA orchestration send --to "bot:<tester>" --chat new --type handoff \
    --subject "BUILD <ID>: <outcome>" --body-file tester-brief.md
```

Each builder bot creates the issue's worktree and [runs its own agent](../../bot-orchestration/references/commands.md)
in it. **Your own agent, only when no bot can take the issue**, gets one new worktree and an
[agent brief](../../bot-orchestration/assets/agent-brief.template.md):

```bash
ORCA orchestration worker-start --spec-file agent-brief-developer.md --agent <harness> --model <model> --effort <effort> \
    --worktree new-child --repo <repo> --name <id-lowercase>
```

`<harness>`, `<model>` and `<effort>` are the cells of the brief's row, the issue's difficulty, in the team's
[agent table](../../bot-orchestration/references/routing.md); drop `--effort` only when the cell says `none`.

Send every issue of a wave together, up to about 4 at once. **Do not send an issue whose `Depends on` names an unmerged
PR**: it goes with the next wave. Then **end your turn**; do not poll.

## 4. The builder reports back

| It is | It sends |
|---|---|
| a builder **bot** | a `status` to the return address, in the [bot report](../../bot-orchestration/assets/bot-report.template.md) format, after it verified the head, ran the handover check and removed the worktree |
| an **agent** | `worker_done` to the bot that started it, as its dispatch preamble says (`--outcome failed` when blocked) |

```bash
ORCA orchestration send --to "bot:<cto>" --chat <return chat id> --type status \
    --subject "PR READY <ID>" --body-file report.md
```

`PR BLOCKED` carries the evidence in `Result` and the one thing needed in `Needs`; that builder keeps its worktree.

## 5. Hand the PR to the reviewer

**The reviewer bot** whenever it exists, with a `handoff` that links the accepted plan:

```bash
ORCA orchestration send --to "bot:<reviewer>" --chat new --type handoff \
    --subject "REVIEW <ID>: PR #<n>" --body-file reviewer-brief.md
```

**Your own agent, only with no reviewer bot**, and never the one that built the PR, with an
[agent brief](../../bot-orchestration/assets/agent-brief.template.md):

```bash
ORCA orchestration worker-start --spec-file agent-brief-reviewer.md --agent <harness> --model <model> --effort <effort> \
    --worktree new-child --repo <repo> --name review-pr-<n>
```

An agent started this way is in a new worktree: it brings the PR branch into it
(`git fetch origin <branch> && git switch -c review/pr-<n> origin/<branch>`). It runs on the issue's
[row](../../bot-orchestration/references/routing.md) of the agent table, and it is never the agent that built the PR. It is of another
model family than the author only where the table gives one; never go around the table to get one.
Then **end your turn**; do not poll.

## 6. The reviewer reports back

| It is | It sends the review report with |
|---|---|
| the reviewer **bot** | `ORCA orchestration send --to "bot:<cto>" --chat <return chat id> --type status --subject "REVIEW PASSED <ID>" --body-file report.md` |
| an **agent** | `worker_done` to the bot that started it, as its dispatch preamble says (`--outcome failed` for a stop) |

## 7. After the merge, or to send it back

```bash
ORCA orchestration send --to "bot:<reviewer>" --chat <its chat id> --type handoff --subject "MERGED <ID>: remove your worktree" --body-file follow-up.md
ORCA orchestration send --to "bot:<reviewer>" --chat <its chat id> --type handoff --subject "<ID>: behind main, rebase and judge the new head" --body-file follow-up.md
ORCA orchestration send --to dispatch:<dispatch_id> --subject "MERGED <ID>: remove your worktree" --body-file follow-up.md
ORCA worktree ps                                       # the builder's and reviewer's worktrees are gone
ORCA orchestration worker-list                         # follow any `next` it shows
```

The first two lines are for a reviewer bot, each a
[follow-up](../../bot-orchestration/assets/follow-up.template.md); the third is for your own agent. `worker-release` closes a terminal; it does
not remove a worktree. Then send the next wave as in section 3.

## 8. A later run

A new run on the same card reads [where it stands](../SKILL.md#where-does-this-run-stand) from the host and goes on
from the first row that is not done.
