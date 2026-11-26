# Orchestration

How the messages of `playbook-complete` travel in Orca. Load the Orca `/orchestration` skill first. Sending issues to
developers and getting their reports back works as in
[the quick orchestration](../../playbook-quick/references/orchestration.md), sections 1 to 3. `ORCA` and the message
types are as in [the plan orchestration](../../playbook-plan/references/orchestration.md); the installed guide and
`ORCA <command> --help` win. Write each body to a file.

## 1. Hand the PR to a reviewer

The reviewer is **another agent** than the developer. Pick the agent and model from the project's agent table or the
human.

```bash
ORCA bot list                                          # is there a reviewer bot?
ORCA orchestration send --to "bot:<reviewer>" --chat new --type question \
    --subject "REVIEW <ID>: PR #<n>" --body-file reviewer-brief.md
# or a supervised worker in its own new worktree
ORCA orchestration worker-start --spec-file reviewer-brief.md --agent <agent> \
    --worktree new-child --repo <repo> --name review-pr-<n>
```

A worker started this way is in a new worktree: it brings the PR branch into it
(`git fetch origin <branch> && git switch -c review/pr-<n> origin/<branch>`). Then **end your turn**; do not poll.

## 2. The reviewer reports back

| The brief came as | Send the review report with |
|---|---|
| a `question` | the reply the incoming message names: `ORCA orchestration reply --id <msg_id> --body-file report.md` |
| a worker dispatch | `worker_done`, as the dispatch preamble says (`--outcome failed` for `REVIEW STOPPED`) |
| a `handoff` | `ORCA orchestration send --to "bot:<cto>" --chat <id> --type handoff --subject "REVIEW PASSED <ID>" --body-file report.md` |

## 3. After the merge, or to send it back

```bash
ORCA orchestration send --to dispatch:<dispatch_id> --subject "MERGED <ID>: remove your worktree" --body-file merged.md
ORCA orchestration send --to dispatch:<dispatch_id> --subject "<ID>: behind main, rebase and judge the new head" --body-file back.md
ORCA worktree ps                                       # the developer's and reviewer's worktrees are gone
ORCA orchestration worker-list                         # follow any `next` it shows
```

For a reviewer bot use `--to "bot:<reviewer>" --chat <id> --type question`. `worker-release` closes a terminal; it does
not remove a worktree.
