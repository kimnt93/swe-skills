# Agents: cli, model, reasoning

Skills and cards name an **agent**, never a model id. An agent is `{cli, model, reasoning}` in one file, the
project's `config.yaml`; `cli` is one of `claude`, `codex`, `omp`, `opencode`. `swe-cli models show` prints the
mapping, `swe-cli models cmd <agent>` prints the exact command a coding CLI runs, and `swe-cli models set <agent>
--cli C --model M --reasoning R` changes one. When a new model ships, only that file changes.

| Agent | Use it for | Never for |
|---|---|---|
| `planner` | splitting a goal into cards; the only agent that needs the strongest model | writing code |
| `developer-junior` | the default for code: a card with a clear description, a named data shape, a failing test to pass, a mechanical refactor | money-path; cross-service design; a bug with no repro |
| `developer-senior` | medium or complex cards: money-path code (orders, fills, positions, balances, risk limits, P&L), cross-service design, subtle concurrency, a bug with no repro, perf work driven by a trace | mechanical edits |
| `reviewer-junior` | the default review: a fast check of the PR against its issue and the card's files | complex or untrusted code |
| `reviewer-senior` | a deeper review: complex cards, money-path, code the human did not write | small, clear cards |
| `documenter`, `scribe`, `verifier` | mechanical work with a deterministic check: docs, changelog entries, lint or format fixes, renames, read-only scouting | money-path; anything whose done-check is a judgment |
| `ci-fixer`, `integrator` | a red check on a PR; bringing a branch up to date with main | anything else |

The workflow gives the build node `developer-junior` and the review node `reviewer-junior`. A planner card names a
stronger agent for a harder card: `"agent": "developer-senior"`, `"reviewer": "reviewer-senior"`.

## Escalation by cause

| What happened | Next attempt |
|---|---|
| hit a context or memory limit | a smaller scope, same agent |
| the connection or process dropped | the same brief, same agent |
| wrong approach, tool error, or the check still fails | the next stronger agent (`developer-senior`) |
| two failed retries | stop and replan around the unit |

## Harnesses

The coding CLIs are `claude`, `codex`, `omp` and `opencode`. Every agent can run on any of them; the mix is whatever
the human configured. There is no cross-family rule: the reviewer is a role, not another vendor.
