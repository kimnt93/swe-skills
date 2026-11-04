# swe-skills

A software-engineering plugin for coding agents. One entry command picks the language for the job,
routes the task to a playbook, the engineering principles and tested skills, and does not finish
until the project's `make verify` passes.

| The job | Language | Skill |
|---|---|---|
| HTTP APIs, services, Kafka consumers, workers | **Go, Fiber v3** (default) | `go-code` |
| ML: training, evaluation, inference, data pipelines | **Python** | `py-code` |
| hot paths, Rust cores for Python, low-latency services | **Rust** | `rust-code` |
| server-rendered web apps | **Next.js** (App Router) | `ts-code` |
| dashboards and internal SPAs | **Vite + React + TypeScript** | `ts-code` | It installs as a plugin in Claude Code, Codex and
oh-my-pi, or as plain skills in Hermes, OpenCode, Gemini CLI and 25 other harnesses. The first version
started from some of the process ideas in [pstack](https://github.com/cursor/plugins/tree/main/pstack)
(MIT); from there it grows with this stack and its requirements.

The plugin's name comes from the build. The default is **`swe`**:

```bash
make claude                      # plugin "swe"   ->  /swe, /swe:go-code, ...
PLUGIN_NAME=acme make claude     # plugin "acme"  ->  /acme, /acme:go-code, ...
```

Build settings live in `plugin.env`. Put private values (your real domain, owner) in a
git-ignored `plugin.local.env`, for example `PLUGIN_DOMAIN ?= mycompany.io`. An environment
variable always wins.

## Documentation

| Read | When |
|---|---|
| [docs/getting-started.md](docs/getting-started.md) | install and the first task, troubleshooting |
| [docs/harnesses.md](docs/harnesses.md) | install into Claude Code, Codex, oh-my-pi and 28 more harnesses (generated) |
| [docs/runbooks.md](docs/runbooks.md) | the steps that need you: pilot service, fleet live, autopilot, publish |
| [docs/context-and-sync.md](docs/context-and-sync.md) | context limits per tool and `/sync` (log in once on the default profile) |
| [docs/setup-claude.md](docs/setup-claude.md) | **Setup A:** Claude Code on your Claude subscription as the coding agent |
| [docs/setup-omp.md](docs/setup-omp.md) | **Setup B:** oh-my-pi as the coding agent |
| [docs/usage.md](docs/usage.md) | what to say for each kind of task; skills; GitHub; the fleet |
| [docs/recommended-setup.md](docs/recommended-setup.md) | the order of work, tiers, the daily routine, what never to do |
| [docs/architecture.md](docs/architecture.md) | the design: roles, flows, invariants, decisions, risks |
| [docs/delegation.md](docs/delegation.md) | tmux sessions in git worktrees: the commands, keeping conflicts small, viewing sessions |
| [docs/agents-and-skills.md](docs/agents-and-skills.md) | which agent gets which skills and GitHub rights |
| [docs/skills/](docs/skills/README.md) | **each skill in detail**: when to use it, what to say, what happens, what you get |
| [docs/skills.md](docs/skills.md) | quick reference for every skill (generated) |

## Use

```text
/swe                                          print the plugin (every skill, grouped)
/swe the orders consumer double-counts fills when Kafka redelivers. repro first, then fix and verify.
/swe:interrogate review this branch
/swe:architect design the position snapshot API
```

| Harness | Entry | Other skills | Subagents |
|---|---|---|---|
| Claude Code | `/swe` | `/swe:<skill>` | `swe:worker`, `swe:adversary` |
| Codex | `$swe:swe` | `$kim:<skill>` | — |
| oh-my-pi | `/skill:swe` | `/skill:<skill>` | omp's own roles |
| Hermes and others | skill `swe` | skill `swe-<skill>` | — |

## Skills

<!-- skills:start -->
40 skills in 6 groups. Click a skill for its detail.

### Start here

| Skill | Description |
|---|---|
| [swe](docs/skills/router.md#router) | Entry point: picks language and playbook, delegates by tier, finishes only when make verify passes |

### Process and proof

| Skill | Description |
|---|---|
| [architect](docs/skills/process.md#architect) | Sketch types and module shape twice, pick one, then implement against it |
| [benchmark-checklist](docs/skills/process.md#benchmark-checklist) | Vet a measured number before you report it or act on it |
| [blast-radius](docs/skills/process.md#blast-radius) | Find what a change could break elsewhere, and prove why it is safe |
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
| [db-migrations](docs/skills/data-platform.md#db-migrations) | PostgreSQL schema changes as goose SQL files, safe by default |
| [db-orm](docs/skills/data-platform.md#db-orm) | Opt-in ORM adapters (bun, SQLAlchemy, SeaORM) behind the same port as raw SQL |

### API and deployment

| Skill | Description |
|---|---|
| [api-contract](docs/skills/data-platform.md#api-contract) | One shape for every HTTP API: /v1, /docs, one /healthz, port 3000, internal token |
| [deployment-setup](docs/skills/data-platform.md#deployment-setup) | Dockerfile, Swarm and local compose, Traefik labels, secrets and CI callers |

### Observability

| Skill | Description |
|---|---|
| [data-realtime-metrics](docs/skills/observability.md#data-realtime-metrics) | The same OTel metric set for every realtime pipeline, one Grafana dashboard |
| [service-errors](docs/skills/observability.md#service-errors) | Unexpected errors to Sentry or GlitchTip, with nothing private leaving |
| [service-logging](docs/skills/observability.md#service-logging) | One JSON log format in Go, Python, TypeScript and Rust, checked by logcheck |
| [service-tracing](docs/skills/observability.md#service-tracing) | OpenTelemetry tracing: service dependencies by default, span detail on request |
<!-- skills:end -->

## Enforced, not just written

| Rule | Enforcer |
|---|---|
| Go data structs: no pointers, no `omitempty` | `go-code/scripts/structcheck` (Go tests; run by `make verify`) |
| Python: no pydantic, no pandas | ruff `TID251` in the py-code template |
| goose migrations: `CONCURRENTLY`, defaults, destructive markers | `db-migrations/scripts/check_migrations.py` |
| API contract: `/v1`, `/docs`, `/healthz`, port 3000 | `api-contract/scripts/audit_api.py`, `probe_api.py` |
| money-path: replay, duplicates, redelivery | `replay-test/scripts/replay.py` |
| TypeScript: strict, no `any`, no `console` | the `ts-code` templates' `tsconfig.json` and ESLint config |
| architecture: layers and imports | Go `archcheck`, Python `lint-imports` (both in `make verify`) |
| a good submit: branch, title, body, issue, size, scope | `github/scripts/pr_lint.py` |
| repo: squash only, protected `main`, labels | `project/scripts/setup_repo.sh` |
| "done" means proven | `verify-create/assets/verify.mk` + the `verify` CI job in `deployment-setup` |

## Make targets

| Target | What it does |
|---|---|
| `make build` | render `dist/<name>/` from `src/` |
| `make validate` | build, then validate (names, links, groups, portability, placeholders) |
| `make <harness>` | build, validate, install: `claude codex omp hermes opencode ...` (`make agents` lists all) |
| `make install` | every harness found on this machine |
| `make <harness> REMOVE=1` | uninstall (only what this tool installed) |
| `make cli` | link the `<name>-cli` command into `~/.local/bin` |
| `make test` | build, enforcement, frontend and cli tests |
| `make docs` | regenerate `docs/skills.md` from the skills |
| `make package` | `dist/<name>-<version>.zip` |
| `make publish` | release `dist/<name>/` into a publish repo, commit and tag (`PUSH=1` pushes) |

## The command: `swe-cli`

`make cli` links `<name>-cli` (default `swe-cli`) into `~/.local/bin`. A project is a directory:

```bash
mkdir orders && cd orders
swe-cli init                          # AGENTS.md (the orchestrator), workflows/, roles.yaml, models.yaml, project.yaml;
                                      # then asks for git URLs until you are done, and clones each one here
swe-cli project add <git url>         # later, from the shell, or ask the orchestrator to do it
swe-cli orchestrate orders            # start the manager agent (any CLI) in this directory
```

The manager takes a request, picks a **workflow** and runs it (`swe-cli flow run orders feature --goal "..."`).
A workflow is a YAML DAG: every node is one agent with only the skills its role needs, on the harness, model
and effort that fit it (documentation runs on the smallest model). Nodes run in parallel, write a report to
a tmp directory, and the last node reports to the manager, which merges the PRs through the gate and runs
`swe-cli flow clean` so nothing stays on the machine. A reviewer agent resolves conflicts when a branch is behind.

Design: [`docs/workflows.md`](docs/workflows.md) (the YAML, roles, reports), [`docs/architecture.md`](docs/architecture.md),
[`docs/agents-and-skills.md`](docs/agents-and-skills.md). Commands: `cli/README.md`.

## Layout

```
plugin.env           build settings (name, owner, version, domain, description)
src/skills/          the skills; src/skills/router/ becomes /<name>
src/agents/          Claude Code subagents (worker, adversary); models from cli/models.yaml
src/manifests/       plugin manifests with placeholders
scripts/             build.py, install.py, validate_skills.py, gen_docs.py, publish.sh
cli/                 the `<name>-cli` command, workflows/, roles.yaml, models.yaml, briefs, tests
docs/                architecture.md (the design), agents-and-skills.md (the recommended setup)
tests/               build_test.sh, enforcement_test.sh, fixtures
LICENSES/           the MIT notice for the pstack ideas the first version started from
CHANGELOG.md         one entry per version (make publish requires it)
dist/                build output (git-ignored); never edit it
```

Agents working in this repo: read `AGENTS.md`, then `docs/README.md`.
