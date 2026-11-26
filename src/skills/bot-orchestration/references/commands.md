# Commands

Load the Orca `/orchestration` skill first; `ORCA` is the executable it resolves to. `ORCA <command> --help` and the
installed guide win over this page. Write each body to a file.

## Your return address

```bash
ORCA bot chats                      # the id on the '(this chat)' line
ORCA bot list                       # the bot names
```

## bot → bot: delegate

```bash
ORCA orchestration send --to "bot:<name>" --chat new --type handoff --subject "<ID>: <outcome>" --body-file delegate.md
ORCA orchestration send --to "bot:<name>" --chat <its chat id> --type handoff --subject "<ID>: changes required" --body-file follow-up.md
```

A handoff returns nothing by itself: the receiving bot **must** send a status to the return address. Then end your turn.

## bot → agent: brief and steer

```bash
ORCA orchestration worker-start --item <n> --spec-file agent-brief.md --agent <harness> --model <model> --effort <effort> \
    --worktree new-child --repo <repo> --name <id-lowercase>
ORCA orchestration send --to dispatch:<dispatch_id> --subject "<ID>: <what changes>" --body-file steer.md
ORCA orchestration reply --id <msg_id> --body-file answer.md          # answer its question
```

`<harness>`, `<model>` and `<effort>` are the three cells of the brief's row in the
[agent table](routing.md); `python3 <this skill>/scripts/agent_table.py row <row>` prints them. Drop `--effort` only
when the cell says `none`; `--effort` works only together with `--model`. Some harnesses cannot take a model in a new
worktree (OpenCode needs an existing one): create it first; `ORCA orchestration worker-start --help` says which. If
Orca cannot give the agent the row's model or effort, report `BLOCKED`; never start it on something else. Start
independent agents together, up to about 4. `--item <n>` only when the bot tracks the job as an item.

## agent → bot: report

The agent uses the commands in its own launch text: `worker_done` once (with the [agent report](../assets/agent-report.template.md)
as its body), `ask` for a question, `escalation` when blocked. Nothing else.

## bot → bot: status

```bash
ORCA orchestration send --to "bot:<name>" --chat <return chat id> --type status \
    --subject "PR READY <ID>" --body-file report.md
```

Send it when the job is done **or** blocked, once for each head you want judged.

## After the job

```bash
ORCA orchestration worker-list                       # every agent settled; follow any `next`
ORCA worktree ps                                     # no finished worktree left
```

## Watching without polling

Orca wakes a bot when a report or a status arrives. To read what is going on without touching it:
`ORCA bot chats --bot "<name>"`, `ORCA orchestration inbox --limit 50`, `ORCA agent read <orca_session_id>`.
