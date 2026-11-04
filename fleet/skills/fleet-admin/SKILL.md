---
name: fleet-admin
description: "How the fleet's admin runs it, whether that is a CLI agent or the optional root Hermes profile: add and sync projects (a directory with its repo clones; with Hermes also a manager profile, board and Hermes project), start each project's orchestrator, check the fleet's health and models, and report across projects. Use whenever you are asked to add a project, start an orchestrator, check the fleet, or report on all projects."
metadata:
  group: process
  summary: "Fleet admin: add projects, start orchestrators, keep the fleet healthy, report across projects"
---

# Fleet admin

You administer the fleet: projects, orchestrators and models. You do not edit repositories, open PRs
or split work into cards: that is each project's orchestrator. If Hermes is enabled (`board.enabled`
in `fleet/models.yaml`) you are its root profile and also route requests to managers.

## Add a project

```bash
fleet project add <name> --dir ~/work/<name> --repo api=<owner>/<repo> [--repo web=<owner>/<repo2>] \
  --description "<one line>" [--cli claude|codex|omp] [--orchestrator claude:mid]
fleet doctor <name>                      # git credentials, tmux or Orca, CLIs, the clones
fleet models check
fleet orchestrate <name>                 # start the project's orchestrator (any CLI) in its directory
```

This writes `fleet/projects.yaml`, creates the directory and clones each repo into it (the same GitHub
repo may belong to several projects: cards are kept apart by branches), and with launcher `orca`
registers the clones in Orca. With Hermes enabled it also creates the manager profile `pm-<name>`,
the board `<name>` and the Hermes project. Then have the orchestrator adopt each repo (the `project`
skill: labels, templates, protected `main`, `ARCHITECTURE.md`, `make verify`).

## Route a request (Hermes only)

1. Find the project: `fleet project list`, then match the request's repo, service or product.
   Ambiguous: ask the human one question naming the candidates.
2. Create one card on that project's board, assigned to its manager, with the request verbatim and
   who asked: `hermes kanban create "<title>" --board <project> --assignee pm-<project>
   --body-file request.md`. Use an `--idempotency-key` from the message id.
3. A request about the fleet itself (a new project, a model change, a profile) is yours.

## Log in once, sync everywhere

Log in on the default profile only (`hermes auth add <provider>`, or a key in `~/.hermes/.env`), then
run `/sync` (the Hermes slash command; `fleet sync` in a shell). It copies provider API keys to every
profile's `.env` (never messaging tokens), applies models, context limits and skills, and reports
logins that are missing or hidden by a profile's own login. Run it after a login, a key rotation,
`fleet project add` or a `fleet/models.yaml` change. OAuth logins need no copy: profiles read the
default's.

## Keep the fleet healthy

- `fleet models check` and `fleet doctor`: 0 problems; `hermes kanban diagnostics --board <each project>`.
- `fleet delegate status <project>` shows each project's running cards.
- A model change: the `model-upgrade` plan (`fleet models apply`, then `make claude omp`).
- Never change another project's board, and never merge.

## Report

Per project, from live state (`gh pr list`, `gh issue list`, `hermes kanban stats --board <p>`),
written per the **ketchup** skill: one line on what waits on the human first.
