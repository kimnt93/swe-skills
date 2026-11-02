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
