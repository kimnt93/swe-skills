---
name: play-docs
description: "Shortcut for the docs playbook: a repo's docs/ is out of date or missing. Restates the goal and its done-predicate, then hands the run to the manager, which starts the docs workflow and reports. Use when the request is: a repo's docs/ is out of date or missing."
metadata:
  group: start
  summary: "Run the docs workflow: follow the code changes, or rewrite docs/ from the code"
---

# Play docs

You start one workflow; you do not do its steps. Each node runs as its own agent in its own worktree.

## Steps

1. Ask for nothing you can read: take the repo, and `rewrite` when docs/ is stale or missing. Restate the goal and the command that proves it in one line; with no
   proof command, ask for it.
2. Do the manager skill's "Before you start a run" (the project's `PROJECT.md` map, `swe-cli doctor`, the architecture).
3. Start it: `swe-cli flow run <project> docs --input repo=<repo> [--input mode=rewrite]`.
4. Watch with `swe-cli flow status <project> <run>`; answer any approval it asks for; report the PRs and what is on main.

## What it does

No planner and a small model: `follow` (the default) compares the code changes since docs/ was last touched; `rewrite` writes docs/ again from the code. Then checks, review, PR.

## Never

Edit code, review or merge by hand, or start a different workflow than the one named here (the manager skill picks others).
