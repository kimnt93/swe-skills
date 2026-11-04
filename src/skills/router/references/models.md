# Model tiers

Skills and cards name a **tier**, never a model id. The ids live in one file, `fleet/models.yaml`
in the stack's repository. `fleet models show` prints the current mapping, and `fleet models cmd <cli> <tier>`
prints the exact command a coding CLI runs. When a new model ships, only that file changes.

| Tier | Use it for | Never for |
|---|---|---|
| `top` | money-path code (orders, fills, positions, balances, risk limits, P&L); cross-service or cross-repo design; subtle concurrency; a bug with no repro; perf work driven by a trace; reviewing another family's code; splitting a large goal into cards | mechanical edits |
| `mid` | the default for code: a feature built from a named data shape, a bug fix with a failing test, a refactor covered by tests, a migration, a contract change | — |
| `low` | mechanical work with a deterministic check: lint or format fixes, renames, running a codemod, dependency bumps with green tests, docstrings, read-only scouting and log reading | money-path; anything whose done-check is a judgment |

## Escalation by cause

| What happened | Next attempt |
|---|---|
| hit a context or memory limit | a smaller scope, same tier |
| the connection or process dropped | the same brief, same tier |
| wrong approach, tool error, or the check still fails | one tier up |
| two failed retries | stop and replan around the unit |

## Families

The two coding CLIs are families: `claude` (Claude models) and `omp` (OpenAI and Google models). A
review is always done by the other family than the one that wrote the code. Inside one harness
you usually can't switch family, so ask for a cross-family review (see [harness](harness.md)).
