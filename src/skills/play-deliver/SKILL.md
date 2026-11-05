---
name: play-deliver
description: "Shortcut for the delivery playbook: any code goal, one repo or several, merged to main without a human. Restates the goal and its done-predicate, then hands the run to the manager, which starts the delivery workflow and reports. Use when the request is: any code goal, one repo or several, merged to main without a human."
metadata:
  group: start
  summary: "Run the delivery workflow for a goal (one or more repos, merged to main)"
---

# Play deliver

You start one workflow; you do not do its steps. Each node runs as its own agent in its own worktree.

## Steps

1. Ask for nothing you can read: take the goal, in one sentence with its acceptance command. Restate the goal and the command that proves it in one line; with no
   proof command, ask for it.
2. Do the manager skill's "Before you start a run" (the project's `PROJECT.md` map, `swe-cli doctor`, the architecture).
3. Start it: `swe-cli flow run <project> delivery --goal "<outcome a caller can observe; the acceptance command>"`.
4. Watch with `swe-cli flow status <project> <run>`; answer any approval it asks for; report the PRs and what is on main.

## What it does

It plans one card per repo from the project's map, every repo builds in parallel against the written interface, a repo that depends on another waits for its merge, then checks, review and merge in turn. It needs `autopilot.auto_merge` to list the card's risk in `config.yaml`; `money-path` waits for the requester.

## Never

Edit code, review or merge by hand, or start a different workflow than the one named here (the manager skill picks others).
