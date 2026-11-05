---
name: play-changelog
description: "Shortcut for the changelog playbook: a PR that needs a CHANGELOG.md entry and has none. Restates the goal and its done-predicate, then hands the run to the manager, which starts the changelog workflow and reports. Use when the request is: a PR that needs a CHANGELOG.md entry and has none."
metadata:
  group: start
  summary: "Run the changelog workflow: add the missing change log entry to a PR"
---

# Play changelog

You start one workflow; you do not do its steps. Each node runs as its own agent in its own worktree.

## Steps

1. Ask for nothing you can read: take the PR number and repo. Restate the goal and the command that proves it in one line; with no
   proof command, ask for it.
2. Do the manager skill's "Before you start a run" (the project's `PROJECT.md` map, `swe-cli doctor`, the architecture).
3. Start it: `swe-cli flow run <project> changelog --input pr=<n> --input repo=<repo>`.
4. Watch with `swe-cli flow status <project> <run>`; answer any approval it asks for; report the PRs and what is on main.

## What it does

A scribe adds the entry on the PR branch, checks run again, a reviewer re-reviews the new head.

## Never

Edit code, review or merge by hand, or start a different workflow than the one named here (the manager skill picks others).
