# Changelog

`make publish` refuses a version without an entry here. This file holds the release notes of the current version only; it does
not track changes between versions.

## 1.0.0

First release. What it is today.

**Skills (41, in six groups)**
- Start and process: the `swe` router and its playbooks, principles, architect, how, why, tdd, deslop, blast-radius, interrogate,
  verify-create, verify-maintain, replay-test, formal-verify, correct, ketchup, reflect, github, project, and the changelog skill
  (a `CHANGELOG.md` entry in every PR, plus the project's `changelog/` directory).
- Roles of workflow agents: manager, planner, developer, reviewer, documenter, intake, integrator, ci-fixer, verifier.
- Languages: Go with Fiber v3 (default for APIs and services), Python (ML and data), Rust (performance), TypeScript (Next.js and
  Vite + React).
- Data: `db-migrations` (goose SQL files), `db-orm` (opt-in GORM for Go and SQLAlchemy 2 for Python behind the same port as raw SQL;
  tested on SQLite and PostgreSQL), `api-contract`, `data-pathway` (realtime pipelines) and `data-dagster` (batch and scheduled
  pipelines). Each of the two has a tested project template, an OTel metric contract, its timeframes and a Grafana dashboard
  checked against the metrics the code emits.
- Platform and observability: deployment-setup, service-logging, service-tracing, service-errors.

**Install**
- A plugin for Claude Code, Codex and oh-my-pi, and plain skills for 52 other harnesses (55 in all). `make install` installs into every detected
  harness, `make <harness>` into one, `make harness` lists them, `swe-cli update` pulls `main` and reinstalls.
- The plugin name, owner and version come from `plugin.env`; the default plugin is `swe`.

**`swe-cli` (`<plugin>-cli`)**
- `swe-cli init` makes a directory a project: `AGENTS.md` (the orchestrator's instructions), `PROJECT.md` (self-learned notes, under
  2000 words), `models.yaml` (the one place that maps tiers top, mid, low to models), `roles.yaml`, `workflows/`, `changelog/`, a
  `learn` skill and `project.yaml` (the repos); it asks for git URLs and clones them. `swe-cli project add` adds a repo later, and
  `swe-cli project update` refreshes the shipped files without overwriting yours.
- Any harness is the orchestrator (`swe-cli orchestrate`). Workflows are YAML DAGs, one agent per node, each with only the skills of its
  role and the model of its tier: feature, bugfix, docs, card, docs-card, ci-fix, conflict, verify, changelog. Agents run in tmux or
  Orca sessions, one git worktree per card, and write reports to a tmp directory.
- The merge gate (`swe-cli merge`, run by `flow merge`) needs the verified head, green required checks, no conflict with `main` and a
  `CHANGELOG.md` entry in the PR (docs, chore, ci, test, style and build PRs and the `no-changelog` label are exempt). After each merge the
  PR is recorded in `changelog/<repo>.md` and `changelog/project.md`. `flow clean` removes every session, worktree, branch and tmp file.
- Also: `delegate`, `lane`, `doctor`, `context`, `models`, `changelog check|record|show`.

**Known limits**
- The Pathway pipeline tests have not been run against a real `pathway` install (the pure-logic tests and the metric checker have).
- The Dagster Dockerfile and compose stack have not been run.
