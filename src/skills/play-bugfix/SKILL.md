---
name: play-bugfix
description: "Shortcut for the bugfix playbook: a defect with a way to reproduce it. Restates the goal and its done-predicate, then hands the run to the manager, which starts the bugfix workflow and reports. Use when the request is: a defect with a way to reproduce it."
metadata:
  group: start
  summary: "Run the bugfix workflow: failing test first, smallest fix, checks, review"
---

# Play bugfix

You start one workflow; you do not do its steps. Each node runs as its own agent in its own worktree.

## Steps

1. Ask for nothing you can read: take the defect and the command that reproduces it. Restate the goal and the command that proves it in one line; with no
   proof command, ask for it.
2. Do the manager skill's "Before you start a run" (the project's `PROJECT.md` map, `swe-cli doctor`, the architecture).
3. Start it: `swe-cli flow run <project> bugfix --goal "<the defect and how to reproduce it>"`.
4. Watch with `swe-cli flow status <project> <run>`; answer any approval it asks for; report the PRs and what is on main.

## What it does

One card whose goal starts with the failing test; then build, checks, review. The report lists the PR.

## Never

Edit code, review or merge by hand, or start a different workflow than the one named here (the manager skill picks others).
