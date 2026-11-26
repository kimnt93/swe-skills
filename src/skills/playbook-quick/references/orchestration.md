# Orchestration

How the messages of `playbook-quick` travel in Orca. Load the Orca `/orchestration` skill first. Resolving `ORCA`, the
message types (`question`, `handoff`, `status`) and the commands for looking at a worker are the same as in
[the plan orchestration](../../playbook-plan/references/orchestration.md); the installed guide and
`ORCA <command> --help` win over both pages. Write each body to a file and pass `--body-file` or `--spec-file`.

## 1. Look before you send

```bash
ORCA bot list                                # is there a developer bot for this project?
ORCA bot chats                               # your own chats; "(this chat)" is the return chat
ORCA worktree ps --since 2h                  # is somebody already on these files?
```

One issue has one developer. If somebody is on it, send to that chat or worker.

## 2. Send the issues

**A. A developer bot.** `question`, so the answer comes back to you. A chat of its own for each issue:

```bash
ORCA orchestration send --to "bot:<developer>" --chat new --type question \
    --subject "BUILD <ID>: <outcome>" --body-file brief-<id>.md
```

A bot developer works from its own home, so it creates one worktree for the issue before it codes:

```bash
ORCA worktree create --repo <repo> --name <id-lowercase> --branch <id-lowercase>/<slug> --base-branch origin/main
```

**B. A supervised worker.** One worker and one new worktree per issue (never `--worktree current`):

```bash
ORCA orchestration worker-start --spec-file brief-<id>.md --agent <agent> \
    --worktree new-child --repo <repo> --name <id-lowercase>
```

Start the issues of one wave together, up to about 4 at once (the `/orchestration` skill's parallel-start reference).
`<agent>` and any model come from the project's agent table or from the human. Then **end your turn**; do not poll.

**Waves as tasks (optional).** To see the waves in one Run:

```bash
ORCA orchestration run-create --objective "<problem>"
ORCA orchestration task-create --task-title "<ID1>" --spec-file brief-<id1>.md
ORCA orchestration task-create --task-title "<ID2>" --spec-file brief-<id2>.md --deps '["<task_id of ID1>"]'
ORCA orchestration task-list --ready --brief
ORCA orchestration worker-start --task <task_id> --agent <agent> --worktree new-child --repo <repo> --name <id-lowercase>
```

**A ready task is not a merged PR.** A task completes when its developer reports. Start a dependent task only after you
have **merged** what it depends on.

## 3. Send the PR back

The developer uses the route the issue came by:

| The issue came as | Send back with |
|---|---|
| a `question` | the reply the incoming message names: `ORCA orchestration reply --id <msg_id> --body-file report.md` |
| a worker dispatch | `worker_done`, exactly as the dispatch preamble says, with the report as its body (`--outcome failed` for `PR BLOCKED`) |
| a `handoff` | the command below: nothing returns by itself |

```bash
ORCA orchestration send --to "bot:<cto>" --chat <return chat id> --type handoff \
    --subject "PR READY <ID>: check and decide" --body-file report.md
```

A developer that needs an answer in the middle uses `ORCA orchestration ask`, as its preamble says, and ends its turn.

## 4. Send feedback

To the **same** developer, so it keeps its branch and context. The body is the decision comment and its URL:

```bash
ORCA orchestration send --to dispatch:<dispatch_id> --subject "<ID>: changes required on PR #<n>" --body-file changes.md
ORCA orchestration send --to "bot:<developer>" --chat <id> --type question \
    --subject "<ID>: changes required on PR #<n>" --body-file changes.md
```

The first is for a worker (a finished one takes it as a follow-up task), the second for a bot. Send at most 3 rounds of
feedback; check with `quick_loop.py decide` before each decision. A rebase request after another merge goes the same way
and is not a round. If the developer is lost, follow the `/orchestration` recovery reference before
starting another on the same branch.

## 5. Clean up

After the merge is **confirmed**, or with the `Stopped` feedback, send the developer one message
([MERGED](../assets/example/cleanup-merged.md), [STOPPED](../assets/example/cleanup-stopped.md)):

```bash
ORCA orchestration send --to dispatch:<dispatch_id> --subject "MERGED <ID>: remove your worktree" --body-file cleanup.md
ORCA orchestration send --to dispatch:<dispatch_id> --subject "STOPPED <ID>: stop and remove your worktree" --body-file cleanup.md
ORCA orchestration send --to "bot:<developer>" --chat <id> --type question --subject "MERGED <ID>: remove your worktree" --body-file cleanup.md
```

The developer checks, reports and removes ([step 8](../SKILL.md#8-developer-remove-the-worktree); a worker sends its
[report](../assets/example/cleanup-report.md) before the removal). Then confirm:

```bash
ORCA worktree ps                              # the issue's worktree is no longer listed
ORCA orchestration worker-list                # follow any `next` it shows for the finished worker
```

`worker-release` closes a settled worker's terminal; it does not remove a worktree.
