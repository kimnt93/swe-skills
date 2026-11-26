---
name: router
description: "Entry point of the @PLUGIN@ plugin for any non-trivial engineering task: picks the language for the job (Go/Fiber for APIs, Python for ML and data, Rust for performance, Next.js or Vite + React + TypeScript for frontends), restates the goal and the done-predicate, picks a playbook, loads the matching skills and principles, delegates by agent (cli, model, reasoning), and does not finish until the project's verify command passes on the committed head. Use at the start of a feature, bug, perf, migration, incident, refactor or investigation, or with no request to list the plugin."
metadata:
  group: start
  summary: "Entry point: picks language and playbook, delegates by agent, finishes only when make verify passes"
---

# @PLUGIN@

The router. You run the playbook in this chat; subagents do bounded pieces.
With no request: print the [skills in this plugin](#skills-in-this-plugin) table and stop.

## Which language

Follow what an existing repo already uses. For new code, pick by the job:

| The job | Language | Skill |
|---|---|---|
| an HTTP API, a service, a Kafka consumer or producer, a worker | **Go, Fiber v3** (the default) | `go-code` |
| ML: training, evaluation, inference, feature pipelines, notebooks, dataframes | **Python** (polars, numpy) | `py-code` (its `ml` and `data` references) |
| a hot path: matching, pricing, indicators, parsers, anything Python or Go is too slow for; Rust cores for Python packages | **Rust** | `rust-code` |
| a web app with server rendering, SEO, or server-side data fetching | **Next.js** (App Router, TypeScript) | `ts-code` (its `nextjs` reference) |
| a dashboard or internal tool as a single-page app | **Vite + React + TypeScript** | `ts-code` (its `vite-react` reference) |

Serve a Python model behind a Go API, or from a small Litestar service when the model must run in
process. Move a measured hot path to Rust, called from Python through PyO3 or run as its own service.
Never start a new HTTP API in Python or Rust without a reason written in the PR.

## Non-negotiables

1. **In your own words first.** Before any edit, state the goal, the smallest change you expect to
   meet it, and the **done-predicate**: a command and its expected output. Don't wait for
   confirmation. If the evidence rules out the requested change, show it and stop.
2. **Pick one pipeline** (`build`, `plan`, `quick`, `review` or `ship`) from the table below: the one the request
   names, else `build`. Open a todo list whose first items are its steps.
3. **Load the domain skill** before you write code. It carries the code standard and tested templates.
4. **Principles.** Read the `principles` index; open each one whose "applies" line matches; name in
   your reply each one that changed a decision. `money-path` always applies to orders, fills,
   positions, balances, risk limits and P&L.
5. **Name the data shape first:** the struct, dataclass, Rust type or TypeScript type, and the table
   or topic it maps to.
6. **A question you could answer by running something is not the human's.** Use the
   [prototype](references/prototype.md) playbook.
7. **Measured numbers** go through the **explain-the-number** principle before you report them.
8. **Done** only when `make verify` exits 0 on the committed head and its tail is in your reply.
9. **Before review**, run the `deslop` skill over the diff.
10. **Respect the architecture.** Read the project's `ARCHITECTURE.md` before a structural change;
    never breach it (`make verify` runs the layering checks). A needed breach is a design change: the
    `architect` skill plus an ADR, in the same PR.
11. **Git and GitHub the one way:** your agent name on every commit and `Created: <agent name>` on every issue,
    comment and PR body; branch from `main`, small Conventional Commits, a PR linked to
    its issue, merge only through the gate (the `github` skill).

## Pipelines: exactly five

Every request that plans, builds or judges a change is one of these; there is no sixth. Every one that builds ends with
the merge.

| Pipeline | Use it for | Flow |
|---|---|---|
| `playbook-build` | **the default**: any request to build that names no playbook | issue → architect plan → CTO/CEO checks it against the card and accepts → code → a PR each → the reviewer checks it against the plan and fixes, ≤3 rounds → CTO/CEO trusts the PASS and merges |
| `playbook-quick` | **only when the request names it**; no plan, **no check** | CTO/CEO issues → code → a PR each → CTO/CEO merges on mechanical conditions only (merge rules, required checks, the reported head, not behind, not a money path) |
| `playbook-plan` | only a plan is wanted | issue → architect plan comment → back to the CTO/CEO → accepts → stop, nothing built |
| `playbook-review` | comment on one existing PR | read → one PASS or FAIL comment → stop, nothing changed or merged |
| `playbook-ship` | take one existing PR to `main` | reviewer reviews and fixes, ≤3 rounds → merges and closes the issue, or stops |

**Choosing.** A request that names a playbook follows it. A CTO/CEO told none uses `playbook-build`; `ship` or `review`
for an existing PR; `plan` when only a plan is wanted. A question is answered read-only, with no pipeline. Nobody picks
`playbook-quick` by itself. Quick named for work with an open design question, or not safe for it (hard, security, a
money path): say so and ask; do not switch silently.

**The weight is on the plan.** By default the owner approves and reviews no code: the architect plans carefully, the
CTO/CEO checks the plan against the card before accepting it, and in `build` and `ship` the reviewer checks the code
against the accepted plan; a departure from it is a finding. A `risk:money-path` change is never merged automatically,
and a project's own approval rules still apply.

The CTO/CEO only orchestrates: it never plans, codes, tests, deploys or reviews code, in any pipeline; each of those jobs
goes to the role that holds it ([bot-orchestration](../bot-orchestration/SKILL.md)). Issues are written with
`write-issue`, comments with `write-comment`, PRs with `work-package`. Anything built or merged passes the
[merge rules](../github/references/pull-requests.md#merge-rules): as shipped, an issue opened by an account with write access
(role admin, maintain or write) or the owner's comment approves it. Only the role the playbook names merges, at the SHA it
checked. A request to plan stops at the accepted plan; a request to review changes nothing.

## Engineering methods

These are methods, not CTO pipelines; use one inside a pipeline when the task needs it.

| Task | Method | Proof |
|---|---|---|
| how does X work / why is it like this | the `how` or `why` skill ([investigation](references/investigation.md)) | file:line and commit evidence |
| defect | [bug-fix](references/bug-fix.md) + `tdd` | failing test first, then verify |
| new behaviour | [feature](references/feature.md) | verify + live probe |
| structure only | [refactoring](references/refactoring.md) | behaviour tests unchanged and green |
| schema change | [migration](references/migration.md) + `db-migrations` | migrate up and down on live PostgreSQL |
| large change across many PRs | [multi-phase](references/multi-phase.md) | each phase green on its own |
| slowness | [perf-issue](references/perf-issue.md) + explain-the-number | baseline vs after, the number explained |
| a profile or trace to read | [profiling](references/profiling.md) | the hot frame at file:line |
| one metric to push | [hillclimb](references/hillclimb.md) | one commit per kept win |
| production symptom | [incident](references/incident.md) | a repro, then bug-fix |
| design fork | [prototype](references/prototype.md), or the `architect` skill for code crossing a function boundary | the chosen sketch |
| get a PR green | [babysit](references/babysit.md) | merge-ready, never merged |
| ship | [opening-a-pr](references/opening-a-pr.md) | PR body with evidence |
| long unattended run | [autonomous-run](references/autonomous-run.md), then `ketchup` | the predicate met |
| take over or stop work | [session-pickup](references/session-pickup.md), [pause-safely](references/pause-safely.md) | — |
| nothing above fits | [figure-it-out](references/figure-it-out.md) | the designed playbook, then its proof |
| change a skill or prompt | [eval](references/eval.md) | blind A/B result |
| a repo's `docs/` is stale or missing | the `docs-sync` skill (`follow` the changes, or `rewrite` from the code) | every command in it runs |

Skills for any playbook: `bot-orchestration` (which bot or agent does the job, and who reports to whom), `github` (branches, PRs, issues, merges), `project` (a project's docs,
repo and backlog), `interrogate` (break a diff), `blast-radius` (what else breaks),
`replay-test` and `formal-verify` (money-path), `verify-create` and `verify-maintain` (the project's
proof), `correct` (a repeated mistake becomes a check), `reflect` (capture what a task taught).

## Subagents

- **Pick an agent, never a model:** `developer-senior`, `developer-junior`, `documenter` ([models](references/models.md));
  [harness](references/harness.md) says how in this harness.
- `developer-junior` is the default for code. `developer-senior` for money-path, cross-service design, concurrency, a bug
  with no repro. `documenter` only for mechanical work with a deterministic check.
- **A second opinion is the same brief on another agent** (a `reviewer-senior` review).
- **You own every subagent's work.** Read its diff; write your own summary.
- **Fresh subagents by default**, with the original brief, every later directive and the prior
  report. Reuse one only for state that lives in it (an uncommitted checkout, a running process).
- Briefs carry file paths, not pasted content.

## Autonomy

- Reversible work proceeds without asking.
- **Always pause** for irreversible writes: force-push to shared branches, deploys, production data,
  messages to customers, and any merge of a money-path change.
- "Don't stop" or "going to bed" means keep going until the predicate is met.
- Give your real judgment; push back when a request doesn't earn its place.

## Writing the reply

Short declarative sentences. Every section the playbook's reply names stays. Frame the impact for the
user of the change and the next maintainer before implementation detail. Every claim carries its
evidence or its label: measured, inferred or guess. Never fabricate a link or a result.

## Comments

Keep a comment only for a non-obvious *why* the code can't show. No phase-narrating comments.

## Skills in this plugin

@SKILL_INDEX@
