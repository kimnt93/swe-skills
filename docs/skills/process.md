# Process and proof skills

The skills that decide *how* to work and *prove* it. The router calls most of them; you can call any of
them directly with `/swe:<skill>`.

## Thinking before code

### how

**What it is.** A senior-engineer walkthrough of a part of the codebase. **Use it when** you are new to a
subsystem or about to change it. **Say.** `/swe:how does the order consumer work?` **What happens.** For a
small scope one pass; for a subsystem 2 to 4 read-only subagents each take an angle, then one merges them.
It follows the flow that matters for the stack: Fiber route, handler, use case, port, adapter, SQL/Redis/Kafka;
topic, decode, handler, transaction, offset commit; data, features, model, serving; route, server or client
component, data hook, API client. **You get** Overview, Key concepts, How it works (with `file:line`), Where
things live, Gotchas, and what was not traced.

### why

**What it is.** The history behind a piece of code. **Use it when** you are about to remove a guard, retry,
flag or odd special case. **Say.** `/swe:why do we retry three times in the order client?` **What happens.**
It anchors the target (`git blame -L`, `git log --follow -p`, `git log -S`), follows PR numbers to
discussions and issues, then checks each source: commits and PRs always, issues, Sentry/GlitchTip for the
exception a guard was added for, Grafana and Loki around the commit date, docs and ADRs; empty sources are
reported too. **You get** what was found (with sources), what can reasonably be inferred (labelled),
competing explanations, what is unknown, and a Preserve / Change / Avoid / Risk list if a change follows.

### architect

**What it is.** Settle types, signatures and module shape before code. **Use it when** code crosses a
function boundary, or for a new service, endpoint, consumer, pipeline or frontend feature. **Say.**
`/swe:architect design the order snapshot API` (add "with checkpoint" to stop for your sign-off).
**What happens.** (1) Ground: map what the code touches. (2) Sketch: at least two runners on row `planner/architect`
(different families when the table offers them) each produce a whole-shape design from the caller's usage, with
`not implemented` bodies; screen them against the red-flags list (pass-through layers, one-implementation
interfaces, boolean parameters, stringly typed values, shared mutable state, I/O in the domain, float money).
(3) Pick a base and graft the best of the other; write the rationale (usage, shape, decision, rejected
alternative, risks). (4) Implement against the sketch; a needed deviation is surfaced, not absorbed.
(5) Scrap and redesign when the same workaround appears repeatedly. **You get** the sketch and rationale.
**Files.** `references/` runner-prompt, design-red-flags, rationale-template.

### principles

**What it is.** The 23 engineering principles, one short file each, with the Go, Python, Rust and
TypeScript forms. **Use it when** the router opens it for you, or when you need the rule behind a review
comment. The full list is in [principles.md](principles.md); the index in `SKILL.md` has one "applies"
line per principle so only the relevant ones are opened.

## Working a change

### tdd

**What it is.** Failing test first, then the smallest change. **Use it when** fixing a bug with a cheap local
test path, or when you ask for TDD or a regression test. **What happens.** Pick the cheapest real level (Go
table test or `-tags e2e`; pytest or `-m integration`; Rust `#[test]` or `proptest`; Vitest or Playwright);
write the test from the caller's view; run it and paste the failure (a typo is not red); make the smallest
change that turns it green; run the whole suite; clean up green. If red could not be shown, it says why and
names the closest check used.

### deslop

**What it is.** Clean a diff before review. **Use it when** before every commit and review. **What it
removes.** Debug output (`fmt.Println`, `print`, `dbg!`, `console.log`), suppressions without a reason
(`//nolint`, `# noqa`, `#[allow]`, `@ts-ignore`), defensive checks for impossible states, dead code,
TODOs without an issue, and comments that restate the code. A comment stating a constraint is kept until a
test or type replaces it. It re-runs formatters, linters and tests after, and tidies PR and commit text.

### blast-radius

**What it is.** What a change could break elsewhere. **Use it when** a small change touches shared code, a
config, a schema, a message format, an API response or a dependency. **What happens.** Read the change
including what the diff doesn't spell out (a default, a renamed JSON field, a NOT NULL column); find the one
fact it is safe because of; look where grep stops (other services calling the `/v1` route, topic consumers,
the generated TypeScript client, wire formats, PyO3 signatures, `deploy/*.env`); rate each risk; prove the
safety fact with code that runs. **You get** the fact and its proof, confirmed risks, and cleared ones.

### interrogate

**What it is.** Adversarial review: only findings proven by a run survive. **Use it when** before shipping a
contested or risky change. **Say.** `/swe:interrogate review this branch`. **What happens.** The scope and
intent are restated; 2 to 3 adversaries (Claude Code: `swe:adversary`; or the other CLI) try to break
the change and must report the exact command and its output; attacks in this stack include duplicate or
out-of-order Kafka messages, a crash between the DB commit and the offset commit, NULL or zero in new columns,
a different ML seed, overflow and panic paths, API error envelopes in the UI. You re-run every finding and
keep only those that reproduce and break the intent. **You get** Intent, Findings (command, output), Dropped.

### security-review

**What it is.** The security and outbound-data check every reviewed pull request gets, for Go, Python, Rust,
TypeScript, web, API, SQL, CI, container, money, wallet, agent and prompt code. Three rules: data leaves only where an
accepted issue asks for that destination and data; a proven finding the change brings in blocks the merge; a finding
needs a proof, run on your own machine, never against a live system. **What happens.** Scan the diff, list every
outbound path, read the diff against each topic it touches (what to look for, a bad and a good example, how to prove
it), prove, and fill the verdict's `## Security` section. **Files.** One page per topic, and
`scripts/security_scan.py`: it lists secrets (never their values), outbound paths, dependencies, risky patterns and
removed controls in a diff, sends nothing, runs nothing from the diff, and exits 2 when it could not scan. It is an aid
with line rules: a clean scan is never a pass.

## Proving it

### verify-create

**What it is.** Gives a project a scripted proof. **Use it when** a repo has no `make verify`, or before
running agents on it unattended. **What happens.** It answers from the repo how to run, health-check, drive
and observe it; copies `assets/verify.mk` (static gates, then a live run that starts the infra and the
service, waits for `/healthz`, probes, and always tears down); vendors the check scripts into `tools/skills/`;
writes a project-local verify skill (Launch, Doctor, Drive, Evidence, Cleanup) and a feature map; proves it
once end to end, then seeds one bug to confirm it fails. **You get** `make verify` and the verify skill.
Per surface the lever includes: Go `golangci-lint`, `go test -race`, `structcheck`, `archcheck`,
`audit_api.py`, `check_migrations.py`, e2e, `probe_api.py`; Python `ruff`, `lint-imports`, `pytest`, an
evaluation against a floor; Rust `fmt`, `clippy -D warnings`, tests; frontends `tsc`, `eslint`, `vitest`,
build, Playwright.

### build-slot

**What it is.** One shared FIFO queue of build slots per user and machine, for heavy builds of any language, so agents
building at once in separate worktrees do not exhaust CPU and memory. **Use it when** you run a heavy build, `make`
target or build script: Cargo and maturin, Go, CMake, make and ninja, large TypeScript builds, Python packages that
compile, Gradle and Maven, `docker build`. **Say.** `swe-build-slot cargo test --workspace --no-run`, then
`cargo test --workspace` outside the slot; `swe-build-slot make build`; `BUILD_SLOT=swe-build-slot make verify` for a
Makefile with the `BUILD_SLOT ?=` prefix variable. **What happens.** The command waits in arrival order for one of 2
slots (`SWE_BUILD_SLOT_MAX`), with its queue position on stderr, runs as given with no shell and returns its exit code.
`CARGO_BUILD_JOBS`, `CMAKE_BUILD_PARALLEL_LEVEL` and Go's `-p` in `GOFLAGS` get `SWE_BUILD_SLOT_JOBS` (6) unless you
set them; `GOMAXPROCS` and `MAKEFLAGS` are never set. A dead or interrupted waiter leaves the queue, a nested call
reuses the outer slot and `SWE_BUILD_SLOT_TIMEOUT` exits 75 without running. The queue lives in `~/.cache/build-slot`
(`SWE_BUILD_SLOT_DIR`), readable by you only, and records the program's name, never its arguments. `make install` puts
the command in `~/.local/bin` (`BIN_DIR`; a `.cmd` launcher on Windows). **You get** at most that many heavy builds at
once. **Files.** `scripts/swe-build-slot.py` (standard library only), tested by `tests/build_slot_test.py`.

### verify-maintain

**What it is.** Keeps the verify skill and its feature map true. **Use it when** periodically and after
features change. **What happens.** Index hygiene; one read-only subagent per feature checks it against the
source (routes, OpenAPI, Next.js or React Router routes, topics, model entry points); you drive every feature
live once on a healthy instance; triage into doc drift (fix), harness gap (fix and re-drive), product bug
(report). **You get** one of: clean, one PR of proven corrections, or blocked with the reason. It edits only
the verify skill's directory and `verify.mk`.

### replay-test

**What it is.** Prove money-path code on a recorded day. **Use it when** for any change to orders, fills,
positions, balances, risk limits or P&L. **What happens.** A recorded event stream goes through a replay
entrypoint that runs the real domain code; `scripts/replay.py check` compares the end state to a golden file
with exact decimals, then again with every event duplicated (`--mutate duplicate`) and with recent events
redelivered (`--mutate redeliver:3`); the end state must not change. `record` refuses to overwrite a golden
file without `--force`. `--self-test` proves the script catches a non-idempotent engine. **Files.**
`scripts/replay.py`, `references/entrypoint.md` (Go, Python, Rust shapes).

### formal-verify

**What it is.** Check every case in a stated scope, where tests cannot reach. **Use it when** an order or
position state machine, retries around a commit, concurrent balance updates, a parser, Rust `unsafe`. **Tools.**
TLA+ (TLC) for bad orderings; property-based tests on the real code (Go `testing/quick` or `rapid`, Python
Hypothesis, Rust `proptest`); Kani for Rust `unsafe` and overflow. **Rules.** Show each property failing on a
broken variant first; a failure on current code is a finding, never a reason to weaken the property; state the
bounds; edit only the verification. **References.** `create` (first check, leaves a project-local skill),
`maintain` (after code changes: replay each counterexample against the real code).

### correct

**What it is.** Make a repeated mistake impossible. **Use it when** you correct an agent for the same thing
twice. **What happens.** Group recent corrections into classes (a class counts once it happened twice); fix
each at the highest level that works: architecture, then types, then a lint or check whose message names the
fix, then a test, docs last; prove each new check fails on a real past mistake; keep a rule to enforcer table
in `AGENTS.md`. **You get** each class with its evidence and the level chosen.

## Testing running software

### web-testing

**What it is.** A test of a web app as its user does it. **Use it when** a UI must be checked or a UI bug needs
evidence. **Say.** `/swe:web-testing test that a customer can get a price on staging` **What happens.** You write a plan
of steps with realistic inputs and the expected result of each; `scripts/web_test.py` runs it in Chromium through
Playwright with real clicks and keystrokes. **You get** per step the input, expected and observed output and a
screenshot; per click a video from the action until the answer arrived, key frames named by time (no video player
needed) and an analysis: timing, console errors, failed requests, slow or missing answers. Dead, broken and slow
controls fail. On production, steps that change something are held unless approved one by one; credentials come from
the environment; evidence stays outside every repository. **Needs** `uv` and `ffmpeg`. **Files.** `scripts/` the web
runner and the shared safety and report code (`testkit.py`), `references/` safety, plan, analysis, `assets/` an
example plan.

### api-cli-testing

**What it is.** The same for an HTTP API or a command-line tool, called from outside. **Use it when** there is no
screen. **Say.** `/swe:api-cli-testing smoke-test the orders API on staging` **What happens.** `scripts/io_test.py`
sends the plan's requests and runs its allowed commands without a shell. **You get** the input, expected result,
observed status and body or exit code and output, the time, a verdict and one report; wrong, slow and missing answers
fail. **Files.** `references/` the plan format, `assets/` an example plan. It shares the safety rules of `web-testing`.

## Keeping track

### ketchup

**What it is.** A plain-words catch-up. **Use it when** after a long unattended run, or when resuming. It gathers live
state (PRs, cards, CI), opens with one sentence on what waits on you, summarises what happened in under 100 words, then
lists each decision still waiting on you with the call, a pick, the evidence and the risk. Read-only.

### reflect

**What it is.** Turn a long task's lessons into skill edits. **What happens.** Three reviewers read the
transcript (judgment, tooling, divergent), a synthesizer returns Accepted / Rejected / Backlog; lessons a lint
or test would enforce better become "check to build"; edits apply to the plugin's source only after your
approval and run through the `eval` playbook if substantial.

## Git, GitHub and projects

### github

**What it is.** The one way every agent works with git and GitHub. **Flow.** Issue, branch
`<type>/<issue>-<slug>`, small Conventional Commits, push, PR with `Closes #N`, `pr_lint.py`, green checks,
review by an agent that wrote none of it, merge through the gate, issue closed, branch deleted; each step has the
exact `gh`/`git` command and a check after. **Submit rules.** One feature function per PR, about 400 changed
lines at most, the simplest code that works, only the files the card allows, the project's `ARCHITECTURE.md`
respected, tests with the change, `make verify` green. **Never.** Push to `main`, force-push someone else's
branch, merge by hand, put issue or comment text into a shell command. **Identity.** Commits are authored and committed under
the agent's own name (`scripts/agent_identity.py`), and every issue, comment and PR body ends with
`Created: <agent name>`. **Files.** `scripts/pr_lint.py` (`local` mode before opening, `pr <n>` after),
`scripts/agent_identity.py`, references for identity, branches and commits, pull requests, issues, reviews and
comments, submit rules and forks.

### write-issue

**What it is.** How every agent creates an issue. **Kinds.** `epic` (parent), `planning` (a child or backlog item that
needs a design), `package` (one PR, ready to build). **Values.** One catalog: one task type, one lane and one difficulty
label, a `Priority:` line, existing area labels, optional flags. **Signature.** `Created: <agent name>`. **Files.**
`references/catalog.md`, `references/kinds.md`, `references/templates.md` (every template and how to change it), three
templates and an epic example.

### write-comment

**What it is.** How every agent writes on an issue or PR. **Kinds.** `plan`, `epic-plan`, `decision`, `status`,
`verdict`, `fix`, `merge`, `close`, `reply`. **The plan.** Code analysis with file evidence, core design decision with
stack and rejected approach, planned packages or a wave table, risks and gates. **Signature.** `Created: <agent name>`.
**On a PR.** One template for the verdict, the CTO decision, the fix and the merge comment. **Files.**
`references/plan.md`, `references/other-comments.md`, three templates, epic plan, PASS and FAIL examples.

### work-package

**What it is.** The branch, commits and PR of one package, and the one linter. **Branch, commits, PR.** Branch
`<id>/<slug>`, commits and PR title `<type>(<id>): <summary>`, the one PR template (the body of every pull request); the author never merges (`playbook-solo` excepted). **Files.** `scripts/package_lint.py` (`issue`,
`comment`, `branch`, `commit`, `pr`, `catalog`, `--self-test`), `assets/catalog.json`, a PR template, one reference.

### project

**What it is.** Run one project's documents, repo and backlog. **Use it when** you are a project manager
profile, or starting or adopting a project. **What it manages.** `README.md`, `ARCHITECTURE.md` (the contract
agents must not breach; a change needs an ADR in the same PR), `docs/adr/`, `CHANGELOG.md`, `RUNBOOK.md`,
`AGENTS.md`; GitHub repo setup through `scripts/setup_repo.sh` (rebase only, branch deleted on merge,
protected `main` with the required `verify` check, linear history, no force push, the catalog labels; `--approvals N`
defaults to 0 because agents share your GitHub account); PR and issue templates; the backlog (one issue per
card, labels mirroring the card, milestones, triage, blocked); status reports from live state.
**Files.** `assets/ARCHITECTURE.md`, `assets/adr.md`, `assets/github/`, `assets/labels.json`.

### changelog

**What it is.** Change logs that stay true across a project of several repos. **Use it when** you open or review a PR that changes
behaviour, the merge gate says the entry is missing, you cut a release, or you ask what changed. **Two layers.** Every repo has a
`CHANGELOG.md` with an `## [Unreleased]` section, and the PR adds its entry **before merge** (not needed for `docs`, `chore`, `ci`,
`test`, `style`, `build` PRs or a `no-changelog` label). The project directory has `changelog/project.md` and one file per repo,
kept by the manager after each merge. **What happens.** A pull request that needs an entry and has none gets a review
finding.
**Say.** `/swe:changelog add the entry for this PR`. **Files.** `references/format.md`, `assets/CHANGELOG.template.md`.

## Roles

The stack has three layers: **Orca** (workspaces, one git worktree per task, orchestration), **Orca bots** (standing role
holders that orchestrate) and **harnesses** (the coding CLIs Orca runs agents in; the plugin installs into each). The
role skills below say how an agent in each role works and what it reports.

### bot-orchestration

**What it is.** How standing bots and the agents they start work together. **Rules.** A bot delegates a job to another bot
with a handoff and gets a status back; a bot briefs its own agents; an agent reports only to the bot that started it.
No agent messages another agent. When a bot has a role, nobody else starts that role's agents. The CEO or CTO only
orchestrates: it writes the issues and runs the playbook, and never plans, codes, tests, deploys or reviews code.
Replies and status reports are short and carry only what the reader needs. Delegated work from one chat to one bot stays in
one child chat on that bot, opened under the parent chat's name; its recorded id is used for every later message.
**Roles.** Architect (plans), developer, tester (only when a request asks for testing), devops (`ops` lane: deployment and operations), reviewer
(code review). The skills name roles only; which bot holds which role is each team's own mapping skill, kept outside
this repository: the orchestrating bot reads it, and otherwise the bot list. **Flow.** CEO bot → issue → the builder bot
of its lane → an agent on the issue's row → verified PR → status to the CEO bot. **The agent table.** One per team, held
by the CTO/CEO, with the rows `simple`, `medium`, `hard` and `planner/architect`, each a harness, a model and a reasoning
effort; the only place that sets them, with no default. **Files.** `assets/agent-table.template.md` (empty),
`scripts/agent_table.py`, `references/routing.md` (which row), `references/commands.md`, an example, five editable message
templates and `scripts/message_lint.py`.

### delegate

**What it is.** One coding task to one Orca worker. **What happens.** A brief that stands alone, with its `Row:` line;
`scripts/delegate.py` reads that row of the agent table and runs `orca orchestration worker-start` with its harness, model
and effort (it has no option to choose any of them, and a missing row stops it); then the diff is read and the check run
before anything lands. **When.** A bot or a person hands a single task to a coding agent. **Files.**
`references/orca-session.md`, `examples/brief-templates.md`, `scripts/delegate.py`, `scripts/discover_agents.py`.

### manager

**What it is.** How a project's manager handles a request. **What happens.** A question it answers read-only. Otherwise
it runs the playbook the request names, or `build` when none is named (`quick` only when named; `solo` it neither runs nor delegates; `plan`, `refactor-plan`,
`review`, `ship`), and delegates each job to the role that holds it, or coordinates its own agents with `delegate`, each
on a row of the agent table. **Never.** Start work on an unapproved issue, or let an author merge its own pull request.

### planner

**What it is.** Turns a goal into PR-sized cards. **What happens.** Reads the architecture and the code, gives
every card disjoint files (its test files among them), a risk, a difficulty, a workflow and a type, orders cards that
share a file, makes no card for tests alone, files one issue
per card and writes the JSON plan the runner fans out over. Read-only on the code.

### developer

**What it is.** Builds one card in its own worktree. **What happens.** Branch from `main`, test first, smallest
change that passes, `make verify` green on the committed head, scope check, push, PR. **What it delivers.** The
complete issue in one PR: the feature, its unit tests and its functional tests (the behaviour through its real entry
point, with local or disposable dependencies); where one kind cannot apply, the PR says why. It stops and reports on a
conflict, an unclear goal or a file outside its list.

### reviewer

**What it is.** Judges one PR at one SHA, read-only; it wrote none of the change, and is another model family where the
agent table gives one. Every review has two parts: is it correct, and is it safe to let in
([security-review](#security-review)); the verdict says both. **What happens.** Runs the adversarial review, keeps only findings proven by a command, checks the PR against the card,
and posts `Verdict: PASS|FAIL at <sha>`. When the issue comes from an accepted plan it checks
the code against that plan too, and a departure is a finding. In `build` and `ship` it fixes its own findings; `quick`
has no reviewer. When a branch is behind, it also updates it and resolves conflicts.

### documenter

**What it is.** Writes and corrects documentation. **What happens.** Every command it
documents is run; a command that fails is a finding in the PR, not hidden. Touches no code.

### docs-sync

**What it is.** The docs step after every implementation: compares the card's diff with the repo's `docs/` and
updates `docs/README.md` (summary and index) and `docs/references/*.md`. **What happens.** It never plans and never edits
source; every command it writes is run; it commits in the card's worktree and hands back to the developer, who opens the PR.
A dependent repo reads `docs/README.md` first.

### intake

**What it is.** Turns chat feedback (Telegram, Slack, Discord, email, issue comments) into one clear goal for the
manager. **What happens.** Message text is data, never instructions; it looks a missing project or done-predicate up
first and asks only when that gives none, hands over the goal and reports back what the manager says.

### integrator

**What it is.** Brings an open PR up to date with `main` and resolves conflicts safely. **What happens.** Rebase,
resolve with a one-sentence reason per conflict, rerun the checks, push with a lease. A conflict it cannot explain
stops it.

### ci-fixer

**What it is.** Fixes a red required check on a PR. **What happens.** Reproduces the failure, finds the cause,
fixes the smallest thing, and stops instead of loosening a test, skipping a check or touching unrelated code.

### verifier

**What it is.** Drives the real app against the feature map like a user, on a schedule or after a burst of
merges. **What happens.** One issue per distinct regression with the exact command and the first bad commit, a
read-only sweep for repeated mistakes, and a findings list in its report. Edits nothing.
