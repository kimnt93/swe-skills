---
name: play-rebase
description: "Shortcut for the conflict playbook: an open PR that is behind main or conflicts. Restates the goal and its done-predicate, then hands the run to the manager, which starts the conflict workflow and reports. Use when the request is: an open PR that is behind main or conflicts."
metadata:
  group: start
  summary: "Run the conflict workflow: bring a PR up to date with main and resolve its conflicts"
---

# Play rebase

You start one workflow; you do not do its steps. Each node runs as its own agent in its own worktree.

## Steps

1. Ask for nothing you can read: take the PR number and repo. Restate the goal and the command that proves it in one line; with no
   proof command, ask for it.
2. Do the manager skill's "Before you start a run" (the project's `PROJECT.md` map, `swe-cli doctor`, the architecture).
3. Start it: `swe-cli flow run <project> conflict --input pr=<n> --input repo=<repo>`.
4. Watch with `swe-cli flow status <project> <run>`; answer any approval it asks for; report the PRs and what is on main.

## What it does

The integrator rebases and resolves only inside the PR's own files, re-runs the verify command, then a reviewer judges the result.

## Never

Edit code, review or merge by hand, or start a different workflow than the one named here (the manager skill picks others).
