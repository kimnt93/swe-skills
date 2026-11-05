---
name: play-land
description: "Shortcut for the land playbook: taking an existing PR, including a human's, all the way to main. Restates the goal and its done-predicate, then hands the run to the manager, which starts the land workflow and reports. Use when the request is: taking an existing PR, including a human's, all the way to main."
metadata:
  group: start
  summary: "Run the land workflow: update, check, review and merge an existing PR without a human"
---

# Play land

You start one workflow; you do not do its steps. Each node runs as its own agent in its own worktree.

## Steps

1. Ask for nothing you can read: take the PR number and repo. Restate the goal and the command that proves it in one line; with no
   proof command, ask for it.
2. Do the manager skill's "Before you start a run" (the project's `PROJECT.md` map, `swe-cli doctor`, the architecture).
3. Start it: `swe-cli flow run <project> land --input pr=<n> --input repo=<repo>`.
4. Watch with `swe-cli flow status <project> <run>`; answer any approval it asks for; report the PRs and what is on main.

## What it does

Brings the branch up to date, waits for checks (a fixer repairs a red one), reviews with fix rounds, then merges through the gate. Needs `autopilot.auto_merge` to list the PR's risk; `money-path` waits for the requester.

## Never

Edit code, review or merge by hand, or start a different workflow than the one named here (the manager skill picks others).
