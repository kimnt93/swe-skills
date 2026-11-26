# Orchestration

How the messages of `playbook-plan` travel in Orca. Load the Orca `/orchestration` skill first, and read the guide the
installed build prints (`ORCA skills get orchestration`): it wins over this page, and `ORCA <command> --help` wins over
both for flags.

`ORCA` is the executable you resolved with the `orca-cli` skill (`ORCA_CLI_COMMAND` when set; on Linux outside an Orca
terminal it is `orca-ide`, never bare `orca`). Write every message body to a file with your file tool and pass
`--body-file` or `--spec-file`.

## 1. Look before you send

```bash
ORCA bot list                                # which bots exist and what each is for
ORCA bot chats --bot "<name>"                # its chats: is this card already being planned?
ORCA bot chats                               # your own chats; the line marked "(this chat)" is your return chat
ORCA worktree ps --since 2h                  # what is running now
```

If somebody is already planning the card, send to that chat or worker. Never start a second architect for one card.

## 2. Send the card to the architect

The messages and their templates are [bot-orchestration](../../bot-orchestration/SKILL.md#the-four-messages).

| Who plans | Pick it when | The plan comes back as |
|---|---|---|
| **A. the architect bot** | `bot list` shows an architect for this project | its `status` to your return address |
| **B. a supervised agent** | no bot has the role | the agent's `worker_done` |

**A. Bot.** Delegate with a `handoff`, from the [delegate template](../../bot-orchestration/assets/delegate.template.md):

```bash
ORCA orchestration send --to "bot:<architect>" --chat new --type handoff \
    --subject "PLAN <ID>: <outcome>" --body-file delegate.md
```

`--chat <id>` continues an earlier chat. A handoff returns nothing by itself, so the brief carries your return address.

**B. Agent.** The spec file is an [agent brief](../../bot-orchestration/assets/agent-brief.template.md).

```bash
ORCA orchestration worker-start --spec-file agent-brief.md --agent <harness> --model <model> --effort <effort> --worktree current
```

`current` is right only when your workspace is a checkout of that repository. Otherwise use
`--worktree new-child --repo <repo> --name <id-lowercase>-plan`. `<harness>`, `<model>` and `<effort>` are the cells of the brief's row,
`planner/architect`, in the team's [agent table](../../bot-orchestration/references/routing.md) (drop `--effort` only when the cell
says `none`); never from this skill or a default, and a missing row means stop and ask. The architect does not
edit tracked files in either case.

After sending, **end your turn**. Do not poll and do not run a watch loop.

## 3. Send the plan back

| You are | Send back with |
|---|---|
| the architect **bot** | a `status` to the return address, in the [bot report](../../bot-orchestration/assets/bot-report.template.md) format |
| an **agent** | `worker_done` to the bot that started you, as the dispatch preamble says (`--outcome failed` when blocked) |

```bash
ORCA orchestration send --to "bot:<cto>" --chat <return chat id> --type status \
    --subject "PLAN READY <ID>" --body-file report.md
```

Without `--chat` it lands in that bot's Home Chat, which may not be the one that asked. An agent that needs an answer in
the middle uses `ORCA orchestration ask`, as its preamble says, and ends its turn. A bot that needs one sends a
`question`.

## 4. Changes required

```bash
ORCA orchestration send --to "bot:<architect>" --chat <id> --type handoff \
    --subject "PLAN <ID> v2: changes required" --body-file follow-up.md
ORCA orchestration send --to dispatch:<id> --subject "PLAN <ID> v2: changes required" --body-file changes.md
```

The first line is for a bot, with a [follow-up](../../bot-orchestration/assets/follow-up.template.md) that links the
decision comment; the second is for your own agent. A finished agent takes it as a follow-up task.

## 5. When you need to look

Orca wakes you when something arrives, so these are for a real doubt ("is it still working?", "what did I miss?"):

| Command | For |
|---|---|
| `ORCA orchestration check` | read your mail when a wake note tells you to; it **takes** the messages it returns |
| `ORCA orchestration inbox` | show earlier messages after you lose context |
| `ORCA orchestration worker-list` | your supervised workers and their state |
| `ORCA orchestration worker-show --dispatch <id>` | one worker, including a prompt it is waiting on |
| `ORCA orchestration worker-read --dispatch <id>` | its recent output |
| `ORCA orchestration worker-stop --dispatch <id>` | stop it, only when the CTO/CEO cancels or replaces the assignment |

Silence or a long run does not prove a worker stopped.

## 6. Optional: a decision gate

Use a gate when the acceptance waits for someone (for example a CEO's decision) and the Run should show it as blocked.
A gate blocks a **task** in a Run; `worker-start` creates a Run, and for route A you create one first.

```bash
ORCA orchestration run-create --objective "Plan <ID>"                          # only when no Run is bound
ORCA orchestration task-create --task-title "Accept plan <ID>" --spec-file accept.md
ORCA orchestration gate-create --task <task_id> --question "Accept plan v1 for <ID>?" \
    --options '["accept","changes required"]'
ORCA orchestration gate-resolve --id <gate_id> --resolution "accept"
ORCA orchestration gate-list --task <task_id>
```

`gate-create` takes `--task` and `--question` (and optionally `--options`). The Run comes from your binding, and the
reason goes into the question. A gate only tracks the wait: the decision still goes on the issue as the CTO/CEO comment.
