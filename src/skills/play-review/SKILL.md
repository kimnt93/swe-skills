---
name: play-review
description: "Shortcut for the review playbook: checking any PR, including one a human wrote. Restates the goal and its done-predicate, then hands the run to the manager, which starts the review workflow and reports. Use when the request is: checking any PR, including one a human wrote."
metadata:
  group: start
  summary: "Run the review workflow: judge a PR at its head, read-only, and post the verdict"
---

# Play review

You start one workflow; you do not do its steps. Each node runs as its own agent in its own worktree.

## Steps

1. Ask for nothing you can read: take the PR number and repo. Restate the goal and the command that proves it in one line; with no
   proof command, ask for it.
2. Do the manager skill's "Before you start a run" (the project's `PROJECT.md` map, `swe-cli doctor`, the architecture).
3. Start it: `swe-cli flow run <project> review --input pr=<n> --input repo=<repo>`.
4. Watch with `swe-cli flow status <project> <run>`; answer any approval it asks for; report the PRs and what is on main.

## What it does

A senior reviewer runs the verify command and the adversarial review at the PR's head, keeps only findings proven by a command, and posts PASS or FAIL. It edits and merges nothing.

## Never

Edit code, review or merge by hand, or start a different workflow than the one named here (the manager skill picks others).
