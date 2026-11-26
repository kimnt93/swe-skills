# Changelog

`make publish` refuses a version without an entry here. This file holds the release notes of the current version only; it does
not track changes between versions.

## [Unreleased]

- **Bots and agents**: new skill `bot-orchestration`. A bot delegates to another bot with a handoff and gets a status back; a bot briefs its own agents; an agent reports only to its bot, and agents never message each other. When a bot has the role, nobody else starts that role's agents. The developer bot picks an agent tier from the issue's difficulty. Five editable message templates (an agent never gets a bot's handoff) and `message_lint.py`, which requires each rule line exactly. An agent started for a role its bot does not hold signs `<bot> / <role>`, so the bot can still judge the PR. `plan`, `quick` and `complete` now delegate with a handoff (not a question). The `developer` skill no longer names two commands that do not exist.
- **Five playbooks**: `plan`, `quick`, and three new ones. `playbook-review` is now comment-only (one verdict on an existing PR). `playbook-ship` reviews a PR, fixes and re-reviews for at most 3 rounds, then merges it and closes its issue, or stops. `playbook-complete` is quick with a separate reviewer who reviews and fixes; the CTO/CEO trusts the PASS and merges. The old build-an-accepted-plan `playbook-review` and the `playbook` dispatcher are removed. `quick_loop.py` is now `github/scripts/pr_loop.py`, with `can-merge` (a PASS on the head, not by the PR's writer, naming the reviewer's own commits; never a money path) and `can-remove --handover`.
- **Merge rules**: a pull request merges only when it links an issue of its repository and every linked issue is approved (the owner's `Accepted by owner.` comment, the owner as author, or board status Todo or In Progress). Done, not planned and duplicate issues are never implemented or merged. `github/scripts/issue_gate.py` checks it before work and before a merge; it refuses when it cannot read the board, and text signed by an agent never counts as the owner's.
- **Quick: feedback limit and cleanup**: each issue is built in its own worktree; the CTO/CEO gives at most 3 feedback rounds, then accepts or posts `Stopped by` with final feedback (the PR stays open, the branch stays on GitHub). After a confirmed merge or a stop the developer removes the worktree. `quick_loop.py` refuses a fourth round and refuses a removal that could lose work.
- **One template per text, and the template is the rule**: every pull request body and every PR comment (verdict, CTO decision, fix, merge) has one template. The linters read sections, order and shapes from the `*.template.md` assets, so editing a template changes the requirement; `AGENT_TEMPLATES=<dir>` overrides them for one project. The GitHub templates for new repositories are copies written by `make docs`. A "Generated with" tool footer fails the lint.
- **Quick pipeline**: `playbook-quick` is now problem → one or more CTO/CEO issues (a parent epic when more than one, in waves) → developer PRs → each sent back to the CTO/CEO → feedback → the CTO/CEO merges the accepted SHA. No separate reviewer; `simple` or `medium` work with no open design question. It ships the orchestration commands and a complete example.
- **Merge and PR checks**: the skills no longer name a `merge` command that does not exist; the merge is `gh pr merge --rebase --match-head-commit` by the role the playbook names. Rebase, not squash: a squash commit is authored by the account that opened the pull request, a rebase keeps the agent's name. `setup_repo.sh` now allows rebase merges only.
- **Issue and comment skills**: added `write-issue` (kinds `epic`, `planning`, `package`; one catalog of task types, lanes, difficulties, priorities and flags) and `write-comment` (nine comment kinds; the plan comment is Code analysis, Core design decision with Stack and Rejected, Planned Packages or a wave table, Risks). `package_lint.py` now checks `issue --kind` and `comment --kind` against the catalog; area labels are optional, a type label and a `Priority:` line are required, and an ID may end in one letter. Repo labels (`project/assets/labels.json`) are generated from the same catalog; `type:*`, `cli:*` and `agent:*` are gone.
- **Agent identity**: every commit is authored and committed under the agent's own name (`github/scripts/agent_identity.py`), and every issue, comment and PR body ends with `Created: <agent name>`; `package_lint.py` and `pr_lint.py` fail otherwise.
- **Plan stops at the accepted plan**: `playbook-plan` is now planning only: CTO/CEO planning card → architect (bot or delegated worker) through Orca orchestration → one plan comment → sent back to the CTO/CEO → acceptance → stop. It ships the orchestration commands and a complete example. `playbook-review` now builds an accepted plan and holds the delegation steps.
- **Work packages**: added the `work-package` skill: one fixed format for a delegable card. Issue `ID: title` with lane, difficulty and area labels and a fixed body (Goal, Read first, Owned files, Forbidden, Depends on, Done when, Branch and PR); branch `<id>/<slug>`; commits and PR `<type>(<id>): <summary>` with Summary, Files changed and Done-when evidence; `scripts/package_lint.py` checks all of it (`--self-test`). `github`'s `pr_lint.py` now accepts a package branch. It now also defines the plan, CTO acceptance, review verdict, fix response and close comments, and the label precedence for lane/difficulty/area plus optional type/risk labels.
- **Playbooks**: replaced the old playbook suite and the `play-*` shortcuts with exactly three CTO pipelines: `playbook-plan` (issue → architect plan comment → CTO acceptance → delegated PRs → reviewer/gate merge), `playbook-review` (the plan pipeline plus reviewer PASS/FAIL and a fix round), and `playbook-quick` (issue → developer PR → reviewer/gate merge, no planning). The `playbook` dispatcher lists only these three. Removed `playbook-deliver`, `playbook-feature`, `playbook-bugfix`, `playbook-review` (old review-only), `playbook-cifix`, `playbook-docs`, `playbook-rebase`, `playbook-land`, `playbook-changelog`, `playbook-verify` and `playbook-solo`.
- **Delegation**: added `delegate` and `orca-cli` skills supporting multi-engine task delegation via Orca CLI sessions, T3 Code threads, or direct headless CLI relays with review-first diff verification.
- **Configuration**: introduced cross-platform `config.json` discovery (`$SWE_CONFIG` -> `./config.json` -> installed plugin directory -> `~/.config/swe/config.json`) and provided `config.example.json`.
- **Simplified CLI**: streamlined `swe-cli` with `swe-cli update` (self-update from git/release), `swe-cli playbooks`, `swe-cli delegate`, `swe-cli config`, and `swe-cli doctor`.
- **Installer**: added root `install.sh` shell script for one-line remote or local installation across all detected AI agent harnesses.

## 1.0.0

First release. What it is today.

**Skills (41, in six groups)**
- Start and process: the `swe` router and its playbooks, principles, architect, how, why, tdd, deslop, blast-radius, interrogate,
  verify-create, verify-maintain, replay-test, formal-verify, correct, ketchup, reflect, github, project, and the changelog skill
  (a `CHANGELOG.md` entry in every PR, plus the project's `changelog/` directory).
- Roles of workflow agents: manager, planner, developer, reviewer, documenter, intake, integrator, ci-fixer, verifier.
- Languages: Go with Fiber v3 (default for APIs and services), Python (ML and data), Rust (performance), TypeScript (Next.js and
  Vite + React).
- Data: `db-migrations` (goose SQL files), `db-orm` (opt-in GORM for Go and SQLAlchemy 2 for Python behind the same port as raw SQL;
  tested on SQLite and PostgreSQL), `api-contract`, `data-pathway` (realtime pipelines) and `data-dagster` (batch and scheduled
  pipelines). Each of the two has a tested project template, an OTel metric contract, its timeframes and a Grafana dashboard
  checked against the metrics the code emits.
- Platform and observability: deployment-setup, service-logging, service-tracing, service-errors.

**Workflows and playbooks**
- `delivery` (several repos, interface first, merged in dependency order, no human), `lane`, `review`, `land`, and `docs` without a
  planner (`follow` or `rewrite`). Every code card runs code, docs, then the PR (`docs-sync` skill). `PROJECT.md` opens with a `# Map`.
- `play-*` shortcut skills (`play-deliver`, `play-bugfix`, `play-docs`, `play-cifix`, `play-rebase`, `play-changelog`, `play-verify`,
  `play-review`, `play-land`) and the `play` dispatcher. `play-solo` runs no workflow: the current harness plans, or takes an
  issue to a merged PR, with no delegation.

**Install**
- A plugin for Claude Code, Codex and oh-my-pi, and plain skills for 52 other harnesses (55 in all). `make install` installs into every detected
  harness, `make <harness>` into one, `make harness` lists them, `swe-cli update` pulls `main` and reinstalls.
- The plugin name, owner and version come from `plugin.env`; the default plugin is `swe`.

**`swe-cli` (`<plugin>-cli`)**
- `swe-cli init` makes a directory a project: `AGENTS.md` (the orchestrator's instructions), `PROJECT.md` (self-learned notes, under
  2000 words), `models.yaml` (the one place that defines the agents: cli, model and reasoning, for claude, codex, omp or opencode), `roles.yaml`, `workflows/`, `changelog/`, a
  `learn` skill and `project.yaml` (the repos); it asks for git URLs and clones them. `swe-cli project add` adds a repo later, and
  `swe-cli project update` refreshes the shipped files without overwriting yours.
- Any harness is the manager (`swe-cli orchestrate`); it answers questions itself and runs workflows for work. Workflows are YAML DAGs, one agent per node, each with only the skills of its
  role and the agent (cli, model, reasoning) it names: feature, bugfix, docs, card, docs-card, ci-fix, conflict, verify, changelog. Agents run in tmux or
  Orca sessions, one git worktree per card, and write reports to a tmp directory.
- The merge gate (`swe-cli merge`, run by `flow merge`) needs the verified head, green required checks, no conflict with `main` and a
  `CHANGELOG.md` entry in the PR (docs, chore, ci, test, style and build PRs and the `no-changelog` label are exempt). After each merge the
  PR is recorded in `changelog/<repo>.md` and `changelog/project.md`. `flow clean` removes every session, worktree, branch and tmp file.
- Also: `delegate`, `lane`, `doctor`, `context`, `models`, `changelog check|record|show`.

**Known limits**
- The Pathway pipeline tests have not been run against a real `pathway` install (the pure-logic tests and the metric checker have).
- The Dagster Dockerfile and compose stack have not been run.
