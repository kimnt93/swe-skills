---
name: delegate
description: "Give one coding task to one Orca worker: write a self-contained brief, start it with `orca orchestration worker-start` on the harness, model and reasoning effort of a row of the team's agent table, then read the diff and run the check before anything lands. Use when a bot or a person hands a single task to a coding agent."
metadata:
  group: process
  summary: "One task to one Orca worker, on a row of the team's agent table; check before landing"
---

# Delegate

One task goes to one coding agent, which Orca runs in a worktree. **Review first:**

1. Write a brief that stands alone: the worker has none of your chat.
2. Start the worker on a row of the team's agent table.
3. Read its diff and run the check yourself. Nothing lands because the worker said so.

**Standing bots:** who delegates to whom, who may start agents and how they report is the
[bot-orchestration](../bot-orchestration/SKILL.md) skill. It comes first; this skill is how one task reaches one
worker.

## 1. The brief

An agent that a bot runs in a playbook gets the
[agent brief](../bot-orchestration/assets/agent-brief.template.md), and commits under the name in it. For a one-off
task whose change you land yourself, use the [brief templates](examples/brief-templates.md): objective, files, the
check command and **no commits**.

Every brief names its **row** (`Row: medium`). [Which row](../bot-orchestration/references/routing.md).

## 2. Start the worker

```bash
python3 <this skill>/scripts/delegate.py --brief brief.md --repo <repo> --name <id-lowercase> --dry-run
python3 <this skill>/scripts/delegate.py --brief brief.md --repo <repo> --name <id-lowercase>
```

The script reads the row from the team's
[agent table](../bot-orchestration/assets/agent-table.template.md) and runs `orca orchestration worker-start` with
that row's harness, model and effort. It has no option to choose any of them. **A missing table or row stops it: ask
the owner.** It never falls back to another row, a default or another way of starting an agent.

`--worktree current` is only for a worker that edits no tracked file, or when your workspace is the task's own. The
commands by hand, steering and cleanup: [the Orca worker](references/orca-session.md). Which harness CLIs this machine
has: `python3 <this skill>/scripts/discover_agents.py`.

## 3. Wait, then check

**End your turn.** Orca wakes you with the worker's `worker_done`, question or escalation; do not poll. Then, in the
worker's worktree:

```bash
git status --short
git diff origin/main...HEAD --stat
make verify        # or the check the brief named
```

Report what you verified, then release the worker.
