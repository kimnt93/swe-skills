# Agents: cli, model, reasoning

Skills and cards name an **agent**, never a model id. An agent is `{cli, model, reasoning}` in one file, the
project's `models.yaml`; `cli` is one of `claude`, `codex`, `omp`, `opencode`. `swe-cli models show` prints the
mapping, `swe-cli models cmd <agent>` prints the exact command a coding CLI runs, and `swe-cli models set <agent>
--cli C --model M --reasoning R` changes one. When a new model ships, only that file changes.

| Agent | Use it for | Never for |
|---|---|---|
| `developer-strong` | money-path code (orders, fills, positions, balances, risk limits, P&L); cross-service or cross-repo design; subtle concurrency; a bug with no repro; perf work driven by a trace; splitting a large goal into cards | mechanical edits |
| `developer` | the default for code: a feature built from a named data shape, a bug fix with a failing test, a refactor covered by tests, a migration, a contract change | — |
| `documenter`, `scribe`, `verifier` | mechanical work with a deterministic check: docs, changelog entries, lint or format fixes, renames, dependency bumps with green tests, read-only scouting and log reading | money-path; anything whose done-check is a judgment |
| `reviewer`, `reviewer-claude` | reviewing another family's code (`reviewers:` picks one by the author's cli) | writing the code under review |

## Escalation by cause

| What happened | Next attempt |
|---|---|
| hit a context or memory limit | a smaller scope, same agent |
| the connection or process dropped | the same brief, same agent |
| wrong approach, tool error, or the check still fails | the next stronger agent (`developer-strong`) |
| two failed retries | stop and replan around the unit |

## Families

The coding CLIs are families by model vendor: `claude` (Claude models), `codex` (OpenAI), `omp` and `opencode`
(whatever providers you logged in to). A review is always done by an agent on another family than the one that wrote
the code (`reviewers:` in `models.yaml`). Inside one harness you usually can't switch family, so ask for a
cross-family review (see [harness](harness.md)).
