# Skills in detail

[../skills.md](../skills.md) is the quick reference (generated). These pages explain each skill: what it is,
when to use it, what to say, what happens, what you get, and its files.

| Page | Covers |
|---|---|
| [router.md](router.md) | `/swe` and its 18 playbooks (bug-fix, feature, refactoring, migration, perf-issue, hillclimb, incident, ...) |
| [process.md](process.md) | how, why, architect, principles, tdd, deslop, blast-radius, interrogate, benchmark-checklist, verify-create, verify-maintain, replay-test, formal-verify, correct, ketchup, reflect, github, project |
| [languages.md](languages.md) | go-code, py-code, rust-code, ts-code |
| [data-platform.md](data-platform.md) | db-migrations, db-orm, api-contract, deployment-setup |
| [observability.md](observability.md) | service-logging, service-tracing, service-errors, data-realtime-metrics |
| [principles.md](principles.md) | the 22 principles, one paragraph each |

## Skills

<!-- skills:start -->
31 skills in 6 groups. Click a skill for its detail.

### Start here

| Skill | Description |
|---|---|
| [swe](router.md#router) | Entry point: picks language and playbook, delegates by tier, finishes only when make verify passes |

### Process and proof

| Skill | Description |
|---|---|
| [architect](process.md#architect) | Sketch types and module shape twice, pick one, then implement against it |
| [benchmark-checklist](process.md#benchmark-checklist) | Vet a measured number before you report it or act on it |
| [blast-radius](process.md#blast-radius) | Find what a change could break elsewhere, and prove why it is safe |
| [correct](process.md#correct) | Make a repeated agent mistake impossible with a check, not a sentence |
| [deslop](process.md#deslop) | Clean a diff before review: debug output, dead code, noisy comments |
| [formal-verify](process.md#formal-verify) | Check state machines, races and retries across every case in a bounded scope |
| [github](process.md#github) | Branch, commit, PR, issue, review and merge the one way, with a check after each step |
| [how](process.md#how) | Explain how a part of the codebase works, with file:line evidence |
| [interrogate](process.md#interrogate) | Adversarial review where only findings proven by a run survive |
| [ketchup](process.md#ketchup) | Plain-words catch-up on what changed and what waits on you |
| [principles](process.md#principles) | 22 engineering principles; the router opens the ones that apply (money-path, idempotency, ...) |
| [project](process.md#project) | Run a project's docs, GitHub repo setup, backlog and status |
| [reflect](process.md#reflect) | Turn a long task's lessons into approved skill edits or new checks |
| [replay-test](process.md#replay-test) | Prove money-path code on a recorded day, with duplicate and redelivery runs |
| [tdd](process.md#tdd) | Failing test first, then the smallest change that makes it pass |
| [verify-create](process.md#verify-create) | Give a project make verify and a verify skill that drives it like a user |
| [verify-maintain](process.md#verify-maintain) | Keep the verify skill and its feature map true as the app changes |
| [why](process.md#why) | Find the history and reasons behind code before changing or removing it |

### Languages

| Skill | Description |
|---|---|
| [go-code](languages.md#go-code) | Default for APIs, services and Kafka consumers: Go with Fiber v3, Postgres, Redis, S3 |
| [py-code](languages.md#py-code) | ML and data in Python: polars, msgspec, and Litestar to serve a model |
| [rust-code](languages.md#rust-code) | Performance: hot paths, Rust cores for Python via PyO3, low-latency services |
| [ts-code](languages.md#ts-code) | Frontends: Next.js (App Router) or Vite + React + TypeScript, with tested templates |

### Data

| Skill | Description |
|---|---|
| [db-migrations](data-platform.md#db-migrations) | PostgreSQL schema changes as goose SQL files, safe by default |
| [db-orm](data-platform.md#db-orm) | Opt-in ORM adapters (bun, SQLAlchemy, SeaORM) behind the same port as raw SQL |

### API and deployment

| Skill | Description |
|---|---|
| [api-contract](data-platform.md#api-contract) | One shape for every HTTP API: /v1, /docs, one /healthz, port 3000, internal token |
| [deployment-setup](data-platform.md#deployment-setup) | Dockerfile, Swarm and local compose, Traefik labels, secrets and CI callers |

### Observability

| Skill | Description |
|---|---|
| [data-realtime-metrics](observability.md#data-realtime-metrics) | The same OTel metric set for every realtime pipeline, one Grafana dashboard |
| [service-errors](observability.md#service-errors) | Unexpected errors to Sentry or GlitchTip, with nothing private leaving |
| [service-logging](observability.md#service-logging) | One JSON log format in Go, Python, TypeScript and Rust, checked by logcheck |
| [service-tracing](observability.md#service-tracing) | OpenTelemetry tracing: service dependencies by default, span detail on request |
<!-- skills:end -->

## Which skill for which situation

| Situation | Start with | Then |
|---|---|---|
| I do not know where to start | `/swe <task>` | the router picks |
| a bug | `/swe fix: ...` (bug-fix) | `tdd`, `interrogate` before shipping |
| a new endpoint or consumer | `/swe add ...` (feature) | `architect`, `go-code`, `api-contract`, `db-migrations` |
| a new page | `/swe add a page ...` | `ts-code`, `api-contract` |
| a model | `/swe train ...` | `py-code` (`ml`), `benchmark-checklist` |
| something is slow | `/swe ... is slow` (perf-issue) | profiling, `benchmark-checklist`, maybe `rust-code` |
| orders, fills, positions, P&L | any task, `money-path` applies | `replay-test`, `formal-verify`, `interrogate`, never auto-merged |
| a schema change | `/swe:db-migrations` | `check_migrations.py`, expand then contract |
| production is wrong | `/swe ... errors spiking` (incident) | `service-errors`, `service-logging`, `service-tracing` |
| a PR needs to be opened or fixed | `/swe:github` | `pr_lint.py`, babysit |
| a repo without `make verify` | `/swe:verify-create` | `verify-maintain` later |
| the agent keeps making the same mistake | `/swe:correct` | `reflect` |
| what happened while I was away | `/swe:ketchup` | |
| a new project to manage | `/swe:project` | `github`, `architect` |

## How the skills fit together

```text
                      /swe  (router)
        language ─► playbook ─► principles ─► subagents by tier ─► make verify
           │            │
           │            ├─ bug-fix ──► tdd ──► (root cause) ──► interrogate ──► github (PR)
           │            ├─ feature ──► how ─► architect ─► domain skill ─► verify-create's lever
           │            ├─ migration ► db-migrations ─► check_migrations.py ─► expand, migrate, contract
           │            └─ perf ─────► profiling ─► benchmark-checklist ─► hillclimb ─► (rust-code)
           │
   go-code | py-code | rust-code | ts-code ──► api-contract, db-*, deployment-setup, service-* (templates)
                                                      │
              checks that fail on a breach: structcheck, archcheck, lint-imports, ruff bans, pr_lint,
              check_migrations, audit_api / probe_api, replay.py  (all run by make verify or the PR flow)
```

## Conventions every skill follows

- A short `SKILL.md` router, one topic per file in `references/`, tested files in `assets/` and `scripts/`.
- A skill names a *tier* (`top`, `mid`, `low`), never a model; model ids live in `fleet/models.yaml`.
- A claim carries its evidence or a label (measured, inferred, guess); "done" means `make verify` passed.
- Anything a skill ships that runs has a test (a `--self-test`, a Go test, or a case in `tests/`).
