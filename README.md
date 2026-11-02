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
oh-my-pi, or as plain skills in Hermes, OpenCode, Gemini CLI and 25 other harnesses. The process
half is forked from Lauren Tan's pstack (MIT; every forked file is listed in `UPSTREAM`).

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
| [docs/setup-claude.md](docs/setup-claude.md) | **Setup A:** Claude Code on your Claude subscription as the coding agent |
| [docs/setup-omp.md](docs/setup-omp.md) | **Setup B:** oh-my-pi as the coding agent |
| [docs/usage.md](docs/usage.md) | what to say for each kind of task; skills; GitHub; the fleet |
| [docs/recommended-setup.md](docs/recommended-setup.md) | the order of work, tiers, the daily routine, what never to do |
| [docs/architecture.md](docs/architecture.md) | the design: roles, flows, invariants, decisions, risks |
| [docs/agents-and-skills.md](docs/agents-and-skills.md) | which agent gets which skills and GitHub rights |
| [docs/skills.md](docs/skills.md) | reference for every skill (generated) |

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

## Skills (31)

| Group | Skills |
|---|---|
| Start here | `swe`: the router (language choice, playbooks, tiers, harness map, reply rules) |
| Process and proof | `principles` (21 + `money-path`), `github`, `project`, `how`, `why`, `tdd`, `architect`, `interrogate`, `blast-radius`, `benchmark-checklist`, `deslop`, `correct`, `verify-create`, `verify-maintain`, `replay-test`, `formal-verify`, `ketchup`, `reflect` |
| Languages | `go-code` (APIs), `py-code` (ML and data), `rust-code` (performance), `ts-code` (Next.js, Vite + React) |
| Data | `db-migrations`, `db-orm` |
| API and deployment | `api-contract`, `deployment-setup` |
| Observability | `service-logging`, `service-tracing`, `service-errors`, `data-realtime-metrics` |

Router playbooks: investigation, bug-fix, feature, refactoring, migration, multi-phase, perf-issue,
profiling, hillclimb, incident, prototype, babysit, opening-a-pr, autonomous-run, session-pickup,
pause-safely, figure-it-out, eval.

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
| `make build` | render `dist/<name>/` from `src/` and `fleet/skills` |
| `make validate` | build, then validate (names, links, groups, portability, placeholders) |
| `make <harness>` | build, validate, install: `claude codex omp hermes opencode ...` (`make agents` lists all) |
| `make install` | every harness found on this machine |
| `make <harness> REMOVE=1` | uninstall (only what this tool installed) |
| `make test` | build, enforcement, frontend and fleet tests |
| `make docs` | regenerate `docs/skills.md` from the skills |
| `make package` | `dist/<name>-<version>.zip` |
| `make publish` | release `dist/<name>/` into a publish repo, commit and tag (`PUSH=1` pushes) |
| `make upstream` | what changed in pstack for the files we forked |

## The fleet

`fleet/` runs the plugin's agents on Hermes Agent, one project per manager:

- **root** (`default` profile): general purpose; manages projects and profiles, routes each request
  to its project, reports across projects.
- **`pm-<project>`**: one manager per project (`fleet project add`); an orchestrator that turns goals
  into GitHub issues and cards that respect the project's `ARCHITECTURE.md`. It never edits code.
- **lanes `claude` and `omp`**: shared by all projects; they implement cards in worktrees through
  Claude Code or oh-my-pi with this plugin, open PRs, and review each other.
- **the merge gate** (`fleet merge`): squash-merges only at the reviewed SHA with green required
  checks, and only for risk classes autopilot allows or with the human's approval.

Every agent and model is set in `fleet/models.yaml`, every project in `fleet/projects.yaml`. Design:
[`docs/architecture.md`](docs/architecture.md). Which agent gets which skills and GitHub rights:
[`docs/agents-and-skills.md`](docs/agents-and-skills.md). Commands: `fleet/README.md`.

## Layout

```
plugin.env           build settings (name, owner, version, domain, description)
src/skills/          the skills; src/skills/router/ becomes /<name>
src/agents/          Claude Code subagents (worker, adversary); models from fleet/models.yaml
src/manifests/       plugin manifests with placeholders
scripts/             build.py, install.py, validate_skills.py, publish.sh, upstream.sh
fleet/               models.yaml, projects.yaml, the fleet command, fleet skills, self-test
docs/                architecture.md (the design), agents-and-skills.md (the recommended setup)
tests/               build_test.sh, enforcement_test.sh, fixtures
UPSTREAM, LICENSES/  where each forked file came from, and pstack's MIT licence
CHANGELOG.md         one entry per version (make publish requires it)
dist/                build output (git-ignored); never edit it
```

Agents working in this repo: read `AGENTS.md`, then `docs/README.md`.
