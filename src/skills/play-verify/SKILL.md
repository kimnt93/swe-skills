---
name: play-verify
description: "Shortcut for the verify playbook: a nightly or after-merge check that the real app still works. Restates the goal and its done-predicate, then hands the run to the manager, which starts the verify workflow and reports. Use when the request is: a nightly or after-merge check that the real app still works."
metadata:
  group: start
  summary: "Run the verify workflow: drive the real app against the feature map and file regressions"
---

# Play verify

You start one workflow; you do not do its steps. Each node runs as its own agent in its own worktree.

## Steps

1. Ask for nothing you can read: take the repo. Restate the goal and the command that proves it in one line; with no
   proof command, ask for it.
2. Do the manager skill's "Before you start a run" (the project's `PROJECT.md` map, `swe-cli doctor`, the architecture).
3. Start it: `swe-cli flow run <project> verify --input repo=<repo>`.
4. Watch with `swe-cli flow status <project> <run>`; answer any approval it asks for; report the PRs and what is on main.

## What it does

Edits nothing: runs the verify command and the feature map, files regressions as issues, logs findings.

## Never

Edit code, review or merge by hand, or start a different workflow than the one named here (the manager skill picks others).
