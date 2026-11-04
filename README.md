# swe-skills

A software-engineering plugin for coding agents. One entry command (`/swe`) picks the language for the job, routes the task to a
playbook, the engineering principles and tested skills, and does not finish until the project's `make verify` passes.
On top of the skills, `swe-cli` runs a **project of agents**: a directory with your repos, where a manager agent turns a request into
a workflow run (plan, build, check, review, merge) with one agent per node.

| The job | Language |
|---|---|
| HTTP APIs, services, Kafka consumers | **Go**, Fiber v3 (default) |
| ML, data pipelines (Pathway, Dagster) | **Python** |
| hot paths, Rust cores for Python | **Rust** |
| web apps and dashboards | **Next.js**, or **Vite + React + TypeScript** |

The full stack is in [STACK.md](STACK.md).

## Setup

```bash
git clone <this repo> && cd swe-skills
make install            # build, validate, install into every harness found on this machine
make claude codex omp   # or only some harnesses (make harness lists all 55)
make cli                # link the swe-cli command into ~/.local/bin
```

## Use

```text
/swe the orders consumer double-counts fills when Kafka redelivers. repro first, then fix and verify.
/swe:interrogate review this branch
```

| Harness | Entry | Another skill |
|---|---|---|
| Claude Code | `/swe` | `/swe:<skill>` |
| Codex | `$swe:swe` | `$swe:<skill>` |
| oh-my-pi | `/skill:swe` | `/skill:<skill>` |
| any other harness | skill `swe` | skill `swe-<skill>` |

## A project of agents

```bash
mkdir orders && cd orders
swe-cli init                  # AGENTS.md, PROJECT.md, models.yaml (tiers), roles.yaml, workflows/; asks for git URLs and clones them
swe-cli orchestrate orders    # start the manager (any harness) in this directory, then ask it for work
swe-cli update                # later: pull main, reinstall everywhere; `swe-cli project update` refreshes this project
```

Tiers (`top`, `mid`, `low`) and the model each one uses are defined in one file, the project's `models.yaml`. How workflows,
roles, reports, change logs and merging work: [docs/workflows.md](docs/workflows.md).

## Documentation

| Read | When |
|---|---|
| [docs/getting-started.md](docs/getting-started.md) | install, first task, troubleshooting |
| [docs/usage.md](docs/usage.md) | what to say for each kind of task |
| [docs/workflows.md](docs/workflows.md) | the project directory, workflows, roles, merge and clean |
| [docs/architecture.md](docs/architecture.md) | the design: roles, flows, invariants, decisions |
| [docs/agents-and-skills.md](docs/agents-and-skills.md) | which agent gets which skills |
| [docs/skills/](docs/skills/README.md) | each skill in detail |
| [docs/harnesses.md](docs/harnesses.md) | every supported harness and how it installs |
| [docs/context.md](docs/context.md) | context limits per tool |
| [docs/recommended-setup.md](docs/recommended-setup.md) | order of work, tiers, the daily routine |
| [docs/development.md](docs/development.md) | make targets, build settings, layout, enforced rules |
| [cli/README.md](cli/README.md) | every `swe-cli` command |

## Skills
<!-- skills:start -->
41 skills in 6 groups. Click a skill for its detail.

### Start here

| Skill | Description |
|---|---|
| [swe](docs/skills/router.md#router) | Entry point: picks language and playbook, delegates by tier, finishes only when make verify passes |

### Process and proof

| Skill | Description |
|---|---|
| [architect](docs/skills/process.md#architect) | Sketch types and module shape twice, pick one, then implement against it |
| [blast-radius](docs/skills/process.md#blast-radius) | Find what a change could break elsewhere, and prove why it is safe |
| [changelog](docs/skills/process.md#changelog) | Change logs: a CHANGELOG.md entry in every PR, plus the project's changelog/ directory |
| [ci-fixer](docs/skills/process.md#ci-fixer) | CI fixer: reproduce a red check locally, fix the cause in the card's files, never weaken the check |
| [correct](docs/skills/process.md#correct) | Make a repeated agent mistake impossible with a check, not a sentence |
| [deslop](docs/skills/process.md#deslop) | Clean a diff before review: debug output, dead code, noisy comments |
| [developer](docs/skills/process.md#developer) | Developer: one card in one worktree, test first, verify on the head, push and open the PR |
| [documenter](docs/skills/process.md#documenter) | Documenter: update docs true to the code, check every command and path, open the PR |
| [formal-verify](docs/skills/process.md#formal-verify) | Check state machines, races and retries across every case in a bounded scope |
| [github](docs/skills/process.md#github) | Branch, commit, PR, issue, review and merge the one way, with a check after each step |
| [how](docs/skills/process.md#how) | Explain how a part of the codebase works, with file:line evidence |
| [intake](docs/skills/process.md#intake) | Intake: turn chat feedback into one clear goal per project, deduped and risk-classified |
| [integrator](docs/skills/process.md#integrator) | Integrator: rebase a PR on main, resolve conflicts only in its own files, re-verify, re-review |
| [interrogate](docs/skills/process.md#interrogate) | Adversarial review where only findings proven by a run survive |
| [ketchup](docs/skills/process.md#ketchup) | Plain-words catch-up on what changed and what waits on you |
| [manager](docs/skills/process.md#manager) | Manager: pick the workflow for a request, start it, watch it, handle approvals, report |
| [planner](docs/skills/process.md#planner) | Planner: split a goal into PR-sized cards with disjoint files, risks and tiers, as a JSON plan |
| [principles](docs/skills/process.md#principles) | 22 engineering principles; the router opens the ones that apply (money-path, idempotency, ...) |
| [project](docs/skills/process.md#project) | Run a project's docs, GitHub repo setup, backlog and status |
| [reflect](docs/skills/process.md#reflect) | Turn a long task's lessons into approved skill edits or new checks |
| [replay-test](docs/skills/process.md#replay-test) | Prove money-path code on a recorded day, with duplicate and redelivery runs |
| [reviewer](docs/skills/process.md#reviewer) | Reviewer: read-only verdict on one SHA, only findings proven by a run, PASS or FAIL |
| [tdd](docs/skills/process.md#tdd) | Failing test first, then the smallest change that makes it pass |
| [verifier](docs/skills/process.md#verifier) | Verifier: run the real app against the feature map, file regressions, list findings; edits nothing |
| [verify-create](docs/skills/process.md#verify-create) | Give a project make verify and a verify skill that drives it like a user |
| [verify-maintain](docs/skills/process.md#verify-maintain) | Keep the verify skill and its feature map true as the app changes |
| [why](docs/skills/process.md#why) | Find the history and reasons behind code before changing or removing it |

### Languages

| Skill | Description |
|---|---|
| [go-code](docs/skills/languages.md#go-code) | Default for APIs, services and Kafka consumers: Go with Fiber v3, Postgres, Redis, S3 |
| [py-code](docs/skills/languages.md#py-code) | ML and data in Python: polars, msgspec, and Litestar to serve a model |
| [rust-code](docs/skills/languages.md#rust-code) | Performance: hot paths, Rust cores for Python via PyO3, low-latency services |
| [ts-code](docs/skills/languages.md#ts-code) | Frontends: Next.js (App Router) or Vite + React + TypeScript, with tested templates |

### Data

| Skill | Description |
|---|---|
| [data-dagster](docs/skills/data-platform.md#data-dagster) | Dagster DAGs: assets, checks, schedules, template, dagster_* OTel metrics, dashboard |
| [data-pathway](docs/skills/data-platform.md#data-pathway) | Realtime Pathway pipelines: Kafka in/out, windows, template, OTel metrics, dashboard |
| [db-migrations](docs/skills/data-platform.md#db-migrations) | PostgreSQL schema changes as goose SQL files, safe by default |
| [db-orm](docs/skills/data-platform.md#db-orm) | GORM (Go) and SQLAlchemy 2 (Python) adapters behind the same port as raw SQL |

### API and deployment

| Skill | Description |
|---|---|
| [api-contract](docs/skills/data-platform.md#api-contract) | One shape for every HTTP API: /v1, /docs, one /healthz, port 3000, internal token |
| [deployment-setup](docs/skills/data-platform.md#deployment-setup) | Dockerfile, Swarm and local compose, Traefik labels, secrets and CI callers |

### Observability

| Skill | Description |
|---|---|
| [service-errors](docs/skills/observability.md#service-errors) | Unexpected errors to Sentry or GlitchTip, with nothing private leaving |
| [service-logging](docs/skills/observability.md#service-logging) | One JSON log format in Go, Python, TypeScript and Rust, checked by logcheck |
| [service-tracing](docs/skills/observability.md#service-tracing) | OpenTelemetry tracing: service dependencies by default, span detail on request |
<!-- skills:end -->
