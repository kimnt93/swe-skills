---
name: project
description: "Run one project: keep its documents (README, ARCHITECTURE.md as the contract agents must not breach, ADRs, CHANGELOG (the changelog skill), RUNBOOK), set up its GitHub repo (labels, templates, squash-only merges, protected main with the required verify check), keep the backlog of issues in step with the workflow cards, and report status. Use when you are a project's manager profile, when starting or adopting a project, or when asked for project status."
metadata:
  group: process
  summary: "Run a project's docs, GitHub repo setup, backlog and status"
---

# Project

A project is one product with its repo(s), its manager. The manager orchestrates; it
never edits product code, and it changes docs only through a PR like anyone else.

| Task | Read |
|---|---|
| which documents a project keeps, and what goes in each | [docs](references/docs.md) |
| set up or audit the GitHub repo | [repo-setup](references/repo-setup.md) (`scripts/setup_repo.sh`) |
| issues ↔ cards, labels, milestones, triage | [backlog](references/backlog.md) |
| weekly or on-request status | [status](references/status.md) |

## The map

`PROJECT.md` opens with a `# Map` block: the project's repos, what each provides and depends on, what is external
(databases, queues, APIs), and the merge order. The manager keeps it true and reads it before every run, because the
planner derives each card's repo and `waits_for` from it. A repo added to `project.yaml` is added to the map in the
same change.

## Change logs

Each repo keeps its own `CHANGELOG.md`; the project directory keeps `changelog/project.md` and `changelog/<repo>.md`. PRs add the
repo entry before merge, the merge gate enforces it and records the merge. Follow the **changelog** skill.

## Starting or adopting a project

1. `scripts/setup_repo.sh <owner>/<repo> --dry-run`, read it, then run it without `--dry-run`.
2. Copy `assets/github/` into the repo's `.github/` (PR and issue templates) and
   `assets/ARCHITECTURE.md` to the repo root; fill it in with the **architect** skill.
3. Add `make verify` (the **verify-create** skill); its CI job becomes the required check.
4. Open one issue per first unit of work and one card per issue (a `swe-cli flow run`).
