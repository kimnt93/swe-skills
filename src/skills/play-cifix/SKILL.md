---
name: play-cifix
description: "Shortcut for the ci-fix playbook: a red required check on an open PR. Restates the goal and its done-predicate, then hands the run to the manager, which starts the ci-fix workflow and reports. Use when the request is: a red required check on an open PR."
metadata:
  group: start
  summary: "Run the ci-fix workflow on a PR whose required check is red"
---

# Play cifix

You start one workflow; you do not do its steps. Each node runs as its own agent in its own worktree.

## Steps

1. Ask for nothing you can read: take the PR number and repo. Restate the goal and the command that proves it in one line; with no
   proof command, ask for it.
2. Do the manager skill's "Before you start a run" (the project's `PROJECT.md` map, `swe-cli doctor`, the architecture).
3. Start it: `swe-cli flow run <project> ci-fix --input pr=<n> --input repo=<repo>`.
4. Watch with `swe-cli flow status <project> <run>`; answer any approval it asks for; report the PRs and what is on main.

## What it does

Reproduces the failure, fixes it on the PR's branch within the card's files, waits for green, reviews.

## Never

Edit code, review or merge by hand, or start a different workflow than the one named here (the manager skill picks others).
