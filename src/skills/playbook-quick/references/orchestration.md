# Orchestration

How the messages of `playbook-quick` travel in Orca. Load the Orca `/orchestration` skill first. Resolving `ORCA`, the
message types (`question`, `handoff`, `status`) and the commands for looking at a worker are the same as in
[the plan orchestration](../../playbook-plan/references/orchestration.md); the installed guide and
`ORCA <command> --help` win over both pages. Write each body to a file and pass `--body-file` or `--spec-file`.

## 1. Look before you send

```bash
ORCA bot list                                # which bot holds the developer role? (or the team's mapping skill)
ORCA bot chats                               # your own chats; "(this chat)" is the return chat
ORCA worktree ps --since 2h                  # is somebody already on these files?
```

One issue has one developer. If somebody is on it, send to that chat or worker.

## 2. Send the issues

**A. The developer bot** (use it whenever it exists). A `handoff` in the
[delegate](../../bot-orchestration/assets/delegate.template.md) format, a chat of its own for each issue:

```bash
ORCA orchestration send --to "bot:<developer>" --chat new --type handoff \
    --subject "BUILD <ID>: <outcome>" --body-file delegate-<id>.md
```

The developer bot then creates the issue's worktree and [runs its own agent](../../bot-orchestration/references/commands.md)
in it. A developer bot that works from its own home creates the issue's worktree first:

```bash
ORCA worktree create --repo <repo> --name <id-lowercase> --branch <id-lowercase>/<slug> --base-branch origin/main
```

**B. Your own agent, only when no bot has the role.** One agent and one new worktree per issue (never
`--worktree current`), briefed with an [agent brief](../../bot-orchestration/assets/agent-brief.template.md):

```bash
ORCA orchestration worker-start --spec-file agent-brief-<id>.md --agent <harness> --model <model> --effort <effort> \
    --worktree new-child --repo <repo> --name <id-lowercase>
```

Start the issues of one wave together, up to about 4 at once (the `/orchestration` skill's parallel-start reference).
`<harness>`, `<model>` and `<effort>` are the cells of the brief's row, the issue's difficulty, in the team's
[agent table](../../bot-orchestration/references/routing.md) (drop `--effort` only when the cell says `none`); a missing row means stop
and ask.
Then **end your turn**; do not poll.

**Waves as tasks (optional).** To see the waves of your own agents in one Run:

```bash
ORCA orchestration run-create --objective "<problem>"
ORCA orchestration task-create --task-title "<ID1>" --spec-file agent-brief-<id1>.md
ORCA orchestration task-create --task-title "<ID2>" --spec-file agent-brief-<id2>.md --deps '["<task_id of ID1>"]'
ORCA orchestration task-list --ready --brief
ORCA orchestration worker-start --task <task_id> --agent <harness> --model <model> --effort <effort> --worktree new-child --repo <repo> --name <id-lowercase>
```

**A ready task is not a merged PR.** A task completes when its agent reports. Start a dependent task only after you
have **merged** what it depends on.

## 3. Send the PR back

| You are | Send back with |
|---|---|
| the developer **bot** | a `status` to the return address, in the [bot report](../../bot-orchestration/assets/bot-report.template.md) format, after you verified the head |
| an **agent** | `worker_done` to the bot that started you, exactly as the dispatch preamble says (`--outcome failed` when blocked) |

```bash
ORCA orchestration send --to "bot:<cto>" --chat <return chat id> --type status \
    --subject "PR READY <ID>" --body-file report.md
```

An agent that needs an answer in the middle uses `ORCA orchestration ask`, as its preamble says, and ends its turn.

## 4. Send it back to the developer

Only for a mechanical reason: a red required check, a branch behind `main` or in conflict, or a head other than the
reported one. First post the [return](../SKILL.md#returns-at-most-3) on the PR (`Return <k> of 3.`, or
`Rebase after #<m>.` once per other quick PR that merged after this PR's latest report or return); `pr_loop.py
decide` refuses a fourth, and then you stop. To the
**same** developer, so it keeps its branch, worktree and context; there is no review feedback:

```bash
ORCA orchestration send --to "bot:<developer>" --chat <its chat id> --type handoff \
    --subject "<ID>: PR #<n> checks red, fix and report the new head" --body-file follow-up.md
ORCA orchestration send --to dispatch:<dispatch_id> --subject "<ID>: PR #<n> behind main, rebase and report" --body-file note.md
```

The first is for the developer's bot (its chat id is on the `From:` line of its report): a
[follow-up](../../bot-orchestration/assets/follow-up.template.md) ([example](../assets/example/rebase.md)). The second is
for your own agent; a finished one takes it as a follow-up task. If an agent is lost, its bot follows the
`/orchestration` recovery reference before starting another on the same branch.

## 5. Clean up

After the merge is **confirmed**, or after your `Stopped`, send the developer one message
([MERGED](../assets/example/cleanup-merged.md), [STOPPED](../assets/example/cleanup-stopped.md)):

```bash
ORCA orchestration send --to dispatch:<dispatch_id> --subject "MERGED <ID>: remove your worktree" --body-file cleanup.md
ORCA orchestration send --to dispatch:<dispatch_id> --subject "STOPPED <ID>: stop and remove your worktree" --body-file cleanup.md
ORCA orchestration send --to "bot:<developer>" --chat <id> --type handoff --subject "MERGED <ID>: remove your worktree" --body-file follow-up.md
```

The developer checks, reports and removes ([step 7](../SKILL.md#7-developer-remove-the-worktree); a worker sends its
[report](../assets/example/cleanup-report.md) before the removal). Then confirm:

```bash
ORCA worktree ps                              # the issue's worktree is no longer listed
ORCA orchestration worker-list                # follow any `next` it shows for the finished worker
```

`worker-release` closes a settled worker's terminal; it does not remove a worktree.
