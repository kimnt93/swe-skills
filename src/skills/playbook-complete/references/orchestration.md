# Orchestration

How the messages of `playbook-complete` travel in Orca. Load the Orca `/orchestration` skill first. Sending issues to
developers and getting their reports back works as in
[the quick orchestration](../../playbook-quick/references/orchestration.md), sections 1 to 3. `ORCA` and the message
types are as in [the plan orchestration](../../playbook-plan/references/orchestration.md); the installed guide and
`ORCA <command> --help` win. Write each body to a file.

## 1. Hand the PR to a reviewer

**The reviewer bot** whenever it exists, with a `handoff` in the
[delegate](../../bot-orchestration/assets/delegate.template.md) format:

```bash
ORCA bot list                                          # is there a reviewer bot?
ORCA orchestration send --to "bot:<reviewer>" --chat new --type handoff \
    --subject "REVIEW <ID>: PR #<n>" --body-file reviewer-brief.md
```

**Your own agent, only with no reviewer bot**, and never the one that built the PR, with an
[agent brief](../../bot-orchestration/assets/agent-brief.template.md):

```bash
ORCA orchestration worker-start --spec-file agent-brief-reviewer.md --agent <agent> \
    --worktree new-child --repo <repo> --name review-pr-<n>
```

An agent started this way is in a new worktree: it brings the PR branch into it
(`git fetch origin <branch> && git switch -c review/pr-<n> origin/<branch>`). Pick the agent from the
[tier table](../../bot-orchestration/references/routing.md), from another model family than the author when there is one.
Then **end your turn**; do not poll.

## 2. The reviewer reports back

| It is | It sends the review report with |
|---|---|
| the reviewer **bot** | `ORCA orchestration send --to "bot:<cto>" --chat <return chat id> --type status --subject "REVIEW PASSED <ID>" --body-file report.md` |
| an **agent** | `worker_done` to the bot that started it, as its dispatch preamble says (`--outcome failed` for a stop) |

## 3. After the merge, or to send it back

```bash
ORCA orchestration send --to "bot:<reviewer>" --chat <its chat id> --type handoff --subject "MERGED <ID>: remove your worktree" --body-file follow-up.md
ORCA orchestration send --to "bot:<reviewer>" --chat <its chat id> --type handoff --subject "<ID>: behind main, rebase and judge the new head" --body-file follow-up.md
ORCA orchestration send --to dispatch:<dispatch_id> --subject "MERGED <ID>: remove your worktree" --body-file follow-up.md
ORCA worktree ps                                       # the developer's and reviewer's worktrees are gone
ORCA orchestration worker-list                         # follow any `next` it shows
```

The first two lines are for a reviewer bot, each a
[follow-up](../../bot-orchestration/assets/follow-up.template.md); the third is for your own agent. `worker-release` closes a terminal; it does
not remove a worktree.
