# 04 — fleet-kit

status: done

## Goal

Every agent of the fleet, at every level, is defined in `fleet/models.yaml`, and one command
builds, checks and runs them.

## What exists

- `fleet/projects.yaml`: one entry per project (repo, GitHub repo, description); `fleet project add | list | sync`
  creates the manager profile `pm-<project>`, the board and the Hermes project.
- `fleet/models.yaml`: `board` (root, the manager template), `lanes` (claude, omp: CLI, brain, tools, skills,
  description), `workers` (per lane and tier), `reviewers`, `subagents` (by tier, rendered into the
  plugin), `omp_roles`, `kanban` (board settings), `autopilot` (risk classes allowed to auto-merge).
- `fleet/bin/fleet`: `models show | check | apply | cmd | reviewer | subagent`, `bootstrap`,
  `lane` (→ `fleet-lane`), `merge` (the autopilot guard), `name`.
- `fleet/bin/fleet-lane`: runs a card or a review, then `make verify`; evidence in `.fleet/`.
- `fleet/skills/fleet-admin` (root), `fleet-manager` (managers), `fleet-worker` (lanes), built into
  `dist/<plugin>/fleet/skills`; every profile also reads the plugin's skills (`github`, `project`, ...).
- `fleet merge --approved`: the manager's path when the human says to merge (any risk, still the SHA and the checks).

## Verify

```bash
bash fleet/tests/selftest.sh --hermes
```

It covers every level of `models.yaml`; a model swap reaching the next card and the plugin's
adversary; apply and bootstrap; lane run and review; the merge guard (refuses when autopilot is off,
for money-path, for another risk class, a stale SHA, red or missing required checks, a closed PR;
merges an allowed one at the verified SHA); and a real bootstrap of a scratch Hermes home, twice.

## Log

- 2026-11-02: projects: root + one manager per project + shared lanes; `fleet project`; `merge --approved`; self-test covers a real bootstrap with two projects.

- 2026-11-02: replaced the separate scripts with one `fleet` command driven by `models.yaml`.
