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

| Who plans | Pick it when | The plan comes back as |
|---|---|---|
| **A. a standing architect bot** | `bot list` shows an architect for this project | the answer to your `question`; it wakes you |
| **B. a supervised worker** | no such bot | the worker's `worker_done`; it wakes you |

**A. Bot.** Use `question`: the planning card stays your job, and the answer returns to you.

```bash
ORCA orchestration send --to "bot:<architect>" --type question \
    --subject "PLAN <ID>: <outcome>" --body-file brief.md
```

Add `--chat new` for a chat of its own, or `--chat <id>` to continue an earlier one.

**B. Worker.** The spec file is the same brief.

```bash
ORCA orchestration worker-start --spec-file brief.md --agent <agent> --worktree current
```

`current` is right only when your workspace is a checkout of that repository. Otherwise use
`--worktree new-child --repo <repo> --name <id-lowercase>-plan`. `<agent>` and any model come from the project's agent
table or from the human, never from this skill. The architect does not edit tracked files in either case.

The three message types are different promises:

| Type | What happens | Use it here for |
|---|---|---|
| `question` | the receiver answers you by mail and that wakes you; you finish the job | **the plan request** |
| `handoff` | the receiver takes over; **nothing comes back by itself** | passing the whole job on, or a return to a chat that asked by handoff |
| `status` | information only: no job, nothing back | telling a third party the plan was accepted |

```bash
ORCA orchestration send --to "bot:<name>" --type status --subject "<news>" --body "<what it means for its work>"
```

After sending, **end your turn**. Do not poll and do not run a watch loop.

## 3. Send the plan back

The architect uses the route the request came by:

| The request came as | Send back with |
|---|---|
| a `question` | the reply the incoming message names: `ORCA orchestration reply --id <msg_id> --body-file report.md` |
| a worker dispatch | `worker_done`, exactly as the dispatch preamble says, with the report as its body (`--outcome failed` for `PLAN BLOCKED`) |
| a `handoff` | a new message to the return address, below |

```bash
ORCA orchestration send --to "bot:<cto>" --chat <return chat id> --type handoff \
    --subject "PLAN READY <ID>: accept or request changes" --body-file report.md
```

A `handoff` return gives the CTO/CEO the next job, which is to confirm. Without `--chat` it lands in that bot's Home
Chat, which may not be the one that asked. A worker that needs an answer in the middle uses `ORCA orchestration ask`, as
its preamble says, and ends its turn.

## 4. Changes required

```bash
ORCA orchestration send --to "bot:<architect>" --chat <id> --type question \
    --subject "PLAN <ID> v2: changes required" --body-file changes.md
ORCA orchestration send --to dispatch:<id> --subject "PLAN <ID> v2: changes required" --body-file changes.md
```

The first line is for a bot, the second for a worker. A finished worker takes it as a follow-up task.

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
