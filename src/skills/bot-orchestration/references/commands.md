# Commands

Load the Orca `/orchestration` skill first; `ORCA` is the executable it resolves to. `ORCA <command> --help` and the
installed guide win over this page. Write each body to a file.

## Your return address

```bash
ORCA bot chats                      # the '(this chat)' line: your chat's id, and its title, your chat's name
ORCA bot list                       # the bot names
```

## bot → bot: delegate

```bash
# the first delegation from this chat to this bot: it opens the child chat
ORCA orchestration send --to "bot:<name>" --chat new --type handoff --subject "<parent chat name>" --body-file delegate.md
ORCA bot chats --bot "<name>"       # the new chat, '<your bot name>: <parent chat name>': record its id

# every later message from this chat to this bot: the next job, then a follow-up
ORCA orchestration send --to "bot:<name>" --chat <child chat id> --type handoff --subject "<ID>: <outcome>" --body-file delegate.md
ORCA orchestration send --to "bot:<name>" --chat <child chat id> --type handoff --subject "<ID>: changes required" --body-file follow-up.md
```

A handoff returns nothing by itself: the receiving bot **must** send a status to the return address. Then end your turn.

## The child chat

[The rule](../SKILL.md#one-child-chat-per-parent-chat-and-bot): one per parent chat and receiving bot.

- **Your chat's name** is the title on the `(this chat)` line. When another bot opened your chat, drop its
  `<sender bot name>: ` prefix: what is left is the subject you pass on.
- **Record** one line per parent chat and receiving bot, `<parent chat id> <bot> <child chat id>`, in your bot's memory
  or in a file outside every repository. A resumed run reads it before it sends anything.
- **Find the new id** with `ORCA bot chats --bot "<name>"`: each row starts with the id, the only thing `--chat` takes.
  If an older chat has the same title, list the chats before and after the send: the new row is yours.
- **A recorded id that is no longer listed is gone.** With no record, a matching title does not make a chat yours:
  open a new one.
- **Seen working:** `--chat new`, then the same id, kept the receiver's context, and replies came back to the sender's
  chat. **Not tried:** sending while the child chat is busy, and chains of more than one child chat. If a message seems
  lost, look (`ORCA bot chats --bot "<name>"`, `ORCA orchestration inbox`) before you send it again.

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
