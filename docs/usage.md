# Usage

How to work with the plugin day to day. Examples use the default name `swe`; in oh-my-pi write
`/skill:swe` for `/swe` and `/skill:<skill>` for `/swe:<skill>`.

## The one habit: start with the router

```text
/swe <what you want, in your words>
```

The router (1) restates your goal and a **done-predicate** (a command and its expected output),
(2) picks the language, (3) picks a playbook, (4) loads the domain skill and the principles that apply,
(5) delegates by tier, and (6) finishes only when `make verify` exits 0 on the committed head, with its
tail in the reply. Called with no request, `/swe` prints the skill table.

### Which language it picks

| The job | Language |
|---|---|
| HTTP APIs, services, Kafka consumers, workers | Go with Fiber v3 (default) |
| ML: training, evaluation, inference, data pipelines | Python (polars, numpy) |
| hot paths, Rust cores for Python, low-latency services | Rust |
| server-rendered web apps | Next.js (App Router) |
| dashboards, internal tools | Vite + React + TypeScript |

## What to say for common tasks

| You say | Playbook the router runs | You get |
|---|---|---|
| `/swe how does the fill consumer work?` | investigation (`how`) | an explanation with `file:line` evidence, no PR |
| `/swe why do we retry three times in the order client?` | investigation (`why`) | the commits, PRs and incidents behind it |
| `/swe fix: cancelled orders still show as open` | bug-fix + `tdd` | a failing test, the root-cause fix, `make verify` |
| `/swe add a cancel-order endpoint and a Cancel button` | feature (`architect` first) | types and a sketch, then code in small commits, then proof |
| `/swe split the orders package, no behaviour change` | refactoring | characterization tests first, then small steps |
| `/swe add a nullable column to orders` | migration + `db-migrations` | expand → migrate → contract, tried up and down on PostgreSQL |
| `/swe the order list endpoint is slow` | perf-issue + profiling | a baseline, the limiter, the fix, a vetted before → after |
| `/swe get p95 under 20 ms` | hillclimb | one change per measurement, one commit per kept win |
| `/swe errors spiking on fills since the deploy` | incident | timeline from Sentry, logs, traces, then a repro |
| `/swe train a model for next-hour volume` | feature with `py-code` ML | time-ordered splits, a model card, an evaluation vs baseline |
| `/swe get PR 42 green` | babysit | conflicts, review threads, CI, stopping at merge-ready |

Skills you can call directly (no router): `/swe:interrogate review this branch`,
`/swe:architect design the position snapshot API`, `/swe:blast-radius`, `/swe:benchmark-checklist`,
`/swe:deslop`, `/swe:ketchup` (catch me up), `/swe:reflect` (capture what this task taught),
`/swe:correct` (stop a repeated mistake). Everything is listed in [skills.md](skills.md), and each skill is explained step by step in [skills/](skills/README.md).

## Give a project proof

"Done" means `make verify` passes. A project without it:

```text
/swe:verify-create        # writes the verify lever, a project-local verify skill and a feature map
/swe:verify-maintain      # later, after features change: keeps them true
```

Then seed one bug and confirm `make verify` fails; make the CI `verify` job a required check.
For orders, fills, positions, balances, risk and P&L also use `/swe:replay-test` (replay a recorded
day, then with duplicated and redelivered events) and, for state machines and races,
`/swe:formal-verify`.

## Git and GitHub, the one way

Every agent follows the `github` skill: issue → branch `<type>/<issue>-<slug>` → small Conventional
Commits → PR with `Closes #N` → `pr_lint.py` clean → checks green → merge through the gate → issue
closed. Say `/swe:github open the PR for this branch` and it writes the body, lints it, opens it and
checks the result. A good submit is one feature function, at most about 400 changed lines, simple
code, only the files the task allows, and the project's `ARCHITECTURE.md` respected.

## With a project of agents (unattended)

A project is a directory. In it, `swe-cli init` writes `AGENTS.md` (the orchestrator's instructions), the
workflows, `roles.yaml`, `models.yaml` and `project.yaml`, and asks for git URLs until you are done. You talk to
the **orchestrator**, any CLI agent started with `swe-cli orchestrate <project>` in that directory. It picks a
workflow and runs it; every node is one agent; the **gate** merges. See [workflows.md](workflows.md).

```text
you → orchestrator: "add cancel-order and a Cancel button"
orchestrator:    swe-cli flow run orders feature --goal "..."
workflow:        plan → two cards in parallel (build → checks → review by another family) → report
orchestrator:    reads the report: "2 PRs ready"; you say "merge"; it runs flow merge, then flow clean
you → orchestrator: "add github.com/acme/billing-api to this project"     (it runs swe-cli project add)
```

Your commands:

```bash
swe-cli init [dir] [--repo <git url>]...   # make a directory a project, add repos
swe-cli project add <git url>              # another repo in this project (project.yaml + clone)
swe-cli orchestrate <name>                 # start the project's orchestrator (any CLI) in its directory
swe-cli flow run|status|retry|merge|clean|stop ...   # what the orchestrator runs; you can too
swe-cli models show | check | apply        # who runs on which model
swe-cli delegate status <project>          # live cards: state, outcome, behind main
tmux attach -t <project>-<card>            # watch or take over a session (or open it in Orca)
```

Risk classes decide what waits for you: `money-path` always; `standard` until you turn on
autopilot for it; `low` after the first 20 clean merges ([recommended-setup.md](recommended-setup.md)).

## Reading what the agent says back

- Claims carry their evidence or a label: *measured*, *inferred*, *guess*.
- The reply ends with the `make verify` tail and what could not be checked.
- A skipped live check is a failure to report, not a footnote.
- If a reply has neither, ask: "what did you run, and what did it print?"
