# The router and its playbooks

`/swe` (the skill `router` in the source) is the one entry point. It does not write code: it decides
how the work will be done, then makes sure it is proven.

### router

**What it is.** The front door of the plugin. It restates the goal, picks the language, picks a playbook,
loads the skills and principles that apply, delegates by model tier, and refuses to finish until
`make verify` passes on the committed head.

**Use it when.** At the start of any non-trivial task: a feature, a bug, a performance problem, a
migration, an incident, a refactor, a question about the code. With no request it prints every skill.

**Say.**
- `/swe` (print the plugin)
- `/swe the orders consumer double-counts fills when Kafka redelivers. repro first, then fix and verify.`
- `/swe add a Cancel button to the orders dashboard`

**What happens.**
1. **In your own words:** it states the goal, the smallest change that meets it, and the *done-predicate* (a command and its expected output). It does not wait for confirmation, but if the evidence rules the request out it shows that and stops.
2. **Language:** the choice follows the job (below). An existing repo's language wins.
3. **Playbook:** it picks one from the table in this page and opens a todo list with that playbook's steps.
4. **Skills and principles:** it loads the domain skill (for example `go-code`) and each principle whose "applies" line matches; `money-path` always applies to orders, fills, positions, balances, risk limits and P&L.
5. **Delegation:** subagents get a tier (`top`, `mid`, `low`), never a model name; the router reads their diffs itself.
6. **Proof:** `make verify` on the committed head; its tail goes in the reply.

**Which language.**

| The job | Language |
|---|---|
| HTTP APIs, services, Kafka consumers, workers | Go with Fiber v3 (default) |
| ML: training, evaluation, inference, data pipelines | Python (polars, numpy) |
| hot paths, Rust cores for Python, low-latency services | Rust |
| server-rendered web apps | Next.js (App Router) |
| dashboards and internal tools | Vite + React + TypeScript |

**You get.** A reply with the goal, what changed, the principles that shaped decisions, the `make verify`
output, and what could not be checked. **Files.** `references/` holds the 18 playbooks below plus
`models.md` (what each tier is for, escalation) and `harness.md` (how to start a subagent, ask the human,
keep a todo list in each harness).

---

## Playbooks

Each playbook is a short procedure with a proof and a reply shape. The router picks one; you can also
say its name ("use the hillclimb playbook").

### investigation

**What it is.** Read-only answers. **Use it when** you ask how something works or why it is that way.
**Steps.** Restate the question; map the subsystem (`how`) or read its history (`why`); cite every claim
with `file:line`, a commit, a PR or a log line; stop and re-route if the answer shows a bug.
**You get** the answer first, then the evidence, then what is still unknown. No PR.

### bug-fix

**What it is.** Reproduce first, fix at the root, prove it on the real surface. **Use it when** something
behaves wrongly. **Steps.** (1) write the failing test at the cheapest real level (Go table case or
`-tags e2e`; pytest; Rust `#[test]` or `proptest`; Vitest or Playwright) and watch it fail for the
reported reason; (2) find the root cause by bisecting hypotheses against git history, Loki logs, Tempo
traces and Sentry; (3) plan the fix (the `architect` skill if it crosses a function boundary) and delegate
it with the test as the target; (4) prove: the test passes, `make verify` passes, the symptom is gone on the
real surface; (5) add a guard only if the bad state is legitimate input. **You get** the root cause in one
sentence and the failing-then-passing test.

### feature

**What it is.** New behaviour, built inside out and proven live. **Use it when** you want something added.
**Steps.** Pick the language; map the affected code (`how`); run `architect`; build in order (Go: domain,
port, adapter, handler, wiring; Python ML: load, features, model, evaluate, artefact, serve; Rust: types,
pure core, I/O at the edge; frontend: API client, data hook, component, route); one commit per verifiable
unit, with independent slices (backend endpoint, frontend page) on parallel subagents once the contract is
settled; prove on the real surface; `interrogate` if the design is contested. **You get** what was built,
the decisions and why, the proof, and open questions.

### refactoring

**What it is.** Change structure, keep behaviour identical. **Use it when** code is hard to follow or to
extend. **Steps.** Pin behaviour with characterization tests through the public surface; delete dead code
first; name the target shape; move in small green steps (migrate every caller and delete the old API in the
same wave; use a codemod for many call sites); keep the change only if it lowers reader load; stop and fix a
bug in its own PR if you find one. **You get** the pin, the steps, and what got simpler.

### migration

**What it is.** Schema and data changes that stay reversible until the last step. **Use it when** a table,
column, index or constraint changes. **Steps.** Name the end state and every reader and writer of the touched
tables; split into expand, migrate (dual-write, batched backfill, switch reads), contract (drop, marked
destructive); lint with `check_migrations.py`; try up, down, up on a real PostgreSQL; measure a backfill's
rows per second before it runs anywhere shared; money-path tables are `top` tier and the contract phase needs
your go. One PR per phase. **You get** the phases, the proof per phase, the backfill numbers.

### multi-phase

**What it is.** A change too big for one PR becomes an ordered list of PRs, each landable and green.
**Use it when** the work spans services or releases. **Steps.** Skip it if one or two PRs suffice; settle
open questions with prototypes; write the phase list with the goal, files, evidence and "must not break" per
phase (deletions, then types/ports/migrations, then behaviour, then callers, then removal of the old path);
each phase is one PR and never depends on a later one. In a `swe-cli` run each phase is a card.

### perf-issue

**What it is.** Measure, then fix from the profile. **Use it when** something is slow or heavy.
**Steps.** Reproduce with a number (`hey`, `k6`, `go test -bench`, `pytest-benchmark`, criterion, Lighthouse);
profile (see `profiling`); fix in order: do less work, batch, cache (with a stated invalidation rule), better
algorithm, then a faster language for the hot path (Rust, measured); re-measure with the same harness and
vet it with the explain-the-number principle. **You get** baseline to after, the limiter, the fix, and proof the number
is real.

### profiling

**What it is.** Reading a profile or trace. **Use it when** you have a capture to interpret.
**Tools.** Go `pprof` and `go tool trace`; Python `py-spy` and `memray`; Rust `cargo flamegraph`, `perf`,
`heaptrack`, `tokio-console`; frontend DevTools and the React Profiler. **Steps.** Open it with the right tool
(large ones in a subagent), find the heaviest frames or retainers, map the hot frame to `file:line`, diff a
before and an after, and label a single profile's reading a hypothesis. **You get** a cited diagnosis.

### hillclimb

**What it is.** Sustained improvement of one metric, one change at a time. **Use it when** you want, for
example, p95 under 20 ms or a model score above a floor. **Steps.** Fix the metric, its direction and a stop
predicate with a floor on attempts; build and freeze a measurement harness (median of N, prints its error
count and the work done); keep a decision log outside the tree; each iteration names a mechanism, a subagent
makes the change in its own worktree, you measure, and keep it only if the metric moves past noise with the
tests green; one commit per kept win; on a plateau change category. **You get** baseline to final, attempts
kept and reverted, and the next idea.

### incident

**What it is.** Diagnose a live symptom from what production already records. **Use it when** errors,
latency or data look wrong right now. **Steps.** Define the symptom precisely; read Sentry/GlitchTip, Loki,
Tempo and Grafana newest first; correlate the first bad timestamp with deploys, config and dependency health;
reduce to a repro (or add missing instrumentation in its own PR); mitigate only reversibly (rollback, flag;
a deploy needs your go); then run `bug-fix` with the repro as the failing test.

### prototype

**What it is.** Throwaway code that settles a question by running it. **Use it when** the open question has a
measurable answer ("is a Redis stream fast enough at 5k msg/s?"). **Steps.** Write the question as a choice;
build the smallest sketch per alternative (2 to 3) in a scratch branch; run each on the same input; present
each option's result and your pick; delete the sketches and carry the decision, not the code.

### babysit

**What it is.** Get a PR to merge-ready; never merge. **Use it when** CI is red, there are review threads or
conflicts. **Steps.** Declare a mode (`drive`, `check`, `threads`); work the lowest unmerged PR of a stack
only; in order: conflicts (report which branch needs a rebase), review threads (verify each claim, fix real ones
with a failing test first), CI (read the failing job's log; a failure outside the diff is a stale base; one
re-run for a flake, a second identical failure is real); batch fixes into one push. **You get** the PR's state
and what waits on a human.

### opening-a-pr

**What it is.** The way every change is submitted. **Steps.** Branch `<type>/<issue>-<slug>`; small
Conventional Commits, each green; formatters, linters and `deslop` before commit; `make verify` on the
committed head; a body with Why, What changed, Scope, Blast radius, Verification and `Closes #N`;
`pr_lint.py` clean; open ready (not draft). Details: the `github` skill.

### autonomous-run

**What it is.** Drive a long task to a checkable predicate without stopping. **Use it when** you say "going
to bed" or "run until done". **Steps.** Write the exit predicate first; pick a wake mechanism for the harness
(`/loop`, `--max-time`, a scheduled `swe-cli flow run`); each iteration makes the smallest justified change, checks it,
commits or reverts; fix blockers yourself in their own PR; log each iteration; stop at the predicate, never
earlier, never by relaxing it. Follow with `ketchup`.

### session-pickup

**What it is.** Take over earlier work without trusting its claims. **Steps.** Find the trail (branch, PR,
card comments, the last transcript of this workspace); rebuild the goal and predicate from the original
request; check real state (`git status`, `gh pr checks`, `make verify`); re-verify every "done"; continue
from the first unproven unit.

### pause-safely

**What it is.** Stop so someone else can resume. **Steps.** Finish or revert the unit in progress; commit a
`wip:` commit and push it (never to `main`); write the handoff (goal, predicate, proven, unproven, next step,
any process to stop) in the PR body or card comment; stop the processes you started.

### figure-it-out

**What it is.** No playbook fits, so design one. **Steps.** Frame (predicate, scope, rigour: more for
one-way doors and money-path); design the workflow (units, riskiest first, harness before work, what runs in
parallel); run the loop with a VERIFIED, NOT VERIFIED or INCONCLUSIVE verdict per unit; keep a decision
trail; hand back after checking the whole against the predicate. If the playbook will recur, propose it as a
new one.

### eval

**What it is.** Change a skill, prompt or model choice only after a blind comparison. **Use it when** you
edit a skill substantially or consider a cheaper model for the manager. **Steps.** Fix 5 to 10 real cases
and what good looks like before running; prepare each candidate in a clean directory; run every case on every
candidate; judge blind with a model from another family; check the transcripts, not the self-reports; keep the
change only if it is not worse on any case that matters. See `docs/runbooks.md` for the model-upgrade use.

### models and harness (references, not playbooks)

`models.md` defines the tiers (`top`: money-path, cross-service design, races, bugs without a repro;
`mid`: the default; `low`: mechanical work with a deterministic check) and the escalation by cause (context
limit: smaller scope; dropped connection: same brief; wrong approach: one tier up; two failures: replan).
`harness.md` maps each abstract action (start a subagent, ask the human, todo list, wake later, project-local
skill path) to Claude Code, oh-my-pi and Codex.

## Play shortcuts

A `play-*` skill starts one workflow and hands the run to the manager; it does no step itself.

### play

**What it is.** Dispatcher: lists the project's workflows, or starts one by name through the manager. **When.** Use when no dedicated `play-*` shortcut fits, or to see the choices.

### play-deliver

**What it is.** Starts the `delivery` workflow for a goal: one repo or several, merged to main without a human. **When.** Needs `autopilot.auto_merge` for the card's risk; `money-path` waits for the requester.

### play-bugfix

**What it is.** Starts `bugfix`: the failing test first, the smallest fix, checks, review. **When.** Give the defect and how to reproduce it.

### play-docs

**What it is.** Starts `docs`: no planner; `follow` the code changes or `rewrite` docs/ from the code. **When.** Give the repo, and `rewrite` for a stale or missing docs/.

### play-cifix

**What it is.** Starts `ci-fix` on an open PR whose required check is red. **When.** Give the PR and repo.

### play-rebase

**What it is.** Starts `conflict`: brings a PR up to date with main and resolves its conflicts, then a review. **When.** Give the PR and repo.

### play-changelog

**What it is.** Starts `changelog`: adds a missing change log entry to a PR. **When.** Give the PR and repo.

### play-verify

**What it is.** Starts `verify`: drives the real app against the feature map and files regressions; edits nothing. **When.** Give the repo.

### play-review

**What it is.** Starts `review`: judges any PR at its head, read-only, and posts PASS or FAIL with proven findings. **When.** Give the PR and repo; it edits and merges nothing.

### play-land

**What it is.** Starts `land`: updates, checks, reviews and merges an existing PR, including a human's, without a human. **When.** Give the PR and repo; `money-path` waits for the requester.

