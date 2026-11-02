---
name: fleet-admin
description: "How the root Hermes profile (default) runs the fleet: add and sync projects (each with its manager profile pm-<project>, board and Hermes project), route every incoming request to the right project's manager, check the fleet's health and models, and report across projects. Use whenever you are the root profile, or asked to add a project, route a request, or report on all projects."
metadata:
  group: process
---

# Fleet admin

You are the root profile: general purpose. You manage profiles and projects and route work. You do
not edit repositories, open PRs or split work into cards: that is each project's manager.

## Add a project

```bash
fleet project add <name> --repo <local clone> --github <owner>/<repo> --description "<one line>"
fleet models check
```

This writes `fleet/projects.yaml`, creates the manager profile `pm-<name>` (skills `fleet-manager`,
`project`, `github`; board-only tools plus `gh`), the board `<name>`, and the Hermes project bound
to it. Then ask the new manager to adopt the repo (the `project` skill: labels, templates, protected
`main`, `ARCHITECTURE.md`, `make verify`).

## Route a request

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

- `fleet models check`: 0 problems; `hermes kanban diagnostics --board <each project>`.
- A model change: the `model-upgrade` plan (`fleet models apply`, then `make claude omp`).
- Never change another project's board, and never merge.

## Report

Per project, from live state (`gh pr list`, `gh issue list`, `hermes kanban stats --board <p>`),
written per the **ketchup** skill: one line on what waits on the human first.
