---
name: play
description: "Dispatcher for the playbooks: lists the workflows a project can run, or starts the one named, handing the run to the manager. Use with a workflow name and its inputs, or with no argument to see the choices, when no dedicated play shortcut fits."
metadata:
  group: start
  summary: "List the project's workflows, or start one by name through the manager"
---

# Play

With no argument, run `swe-cli flow list` and show each workflow with its inputs, plus the dedicated shortcuts:
the play-deliver, play-bugfix, play-docs, play-cifix, play-rebase, play-changelog, play-verify, play-review and play-land skills,
and play-solo, which runs no workflow: you do the steps yourself in this chat.

With a name, follow the manager skill: restate the goal and its proof, check the project, then
`swe-cli flow run <project> <name> --goal "..." [--input k=v ...]`. A project's own workflows in its
`workflows/` directory are listed too, so a new workflow is usable the day it is added.

## Never

Do a workflow's steps yourself, or guess a workflow name that `swe-cli flow list` does not show.
