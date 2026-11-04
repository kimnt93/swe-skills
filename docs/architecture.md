# Architecture: the swe-skills agents

How the plugin and its agents run several software projects with any CLI agent as the orchestrator
(Claude Code, Codex, oh-my-pi), with GitHub as the place where all code lands. Written in the `architect` skill's rationale shape: usage first, then
the shape, then the decisions and what was rejected.

## Usage

What the human types, and what happens:

```text
(in the orchestrator's CLI)
"orders: add an endpoint to cancel an open order, and a Cancel button on the dashboard"

orchestrator   → the agent started by `swe-cli orchestrate orders` in the project directory ~/work/orders
                 (repos api/ and web/): reads ARCHITECTURE.md; creates issues #41 (API) and #42 (UI) and,
                 for each, the files it may touch; checks that no open card overlaps them
                 swe-cli delegate start orders c41 --repo api --files internal/orders/ --branch feat/41-cancel-order
                 swe-cli delegate start orders c42 --repo web --files src/orders/ --cli codex
sessions       → orders-c41: Claude Code (/swe) in its own worktree ~/work/orders/.wt/api/feat-41-cancel-order:
                 test first, code, sync-branch, make verify, PR "feat(orders): cancel an open order"
                 (Closes #41), last line "CARD DONE <sha> <pr>"
orchestrator   → swe-cli delegate status orders c41 → short result; swe-cli delegate review orders c41
                 (another CLI family, read-only) → "Verdict: PASS at <sha>"
human          → "merge #41"        (conflicts and money-path reviews are also yours, in the CLI)
orchestrator   → swe-cli merge 41 --approved --sha <sha> → squash-merged; swe-cli delegate cleanup orders c41
```

## Shape

```
 human ──► orchestrator  (any CLI agent: claude / codex / omp, one per project, started in the project dir)
           skills manager, project, github   issues, briefs, swe-cli delegate, status, merge gate
              │ swe-cli delegate start / status / send / review / cleanup
              ▼
   project directory  ~/work/<project>/
        api/  web/  …      central clones (main, never edited): one project may hold several repos
        .wt/<repo>/<branch>   one git worktree per card
              │
   session <project>-<card>  ──  Claude Code, Codex or oh-my-pi + the swe plugin
   (tmux: tmux attach -t <project>-<card>;  launcher orca: a terminal in the Orca app, next to the worktree)
              │ branch <type>/<issue>-<slug>, sync-branch before the PR
              ▼
   GitHub: PR → required check "verify" → swe-cli merge (the gate) → main
```

| Piece | Where it is defined | Writes code? | Merges? |
|---|---|---|---|
| manager (any CLI) | the project's `config.yaml` `manager` (an agent), per project `manager:` in `project.yaml`; started by `swe-cli orchestrate` | no | only with the human's approval (`swe-cli merge --approved`), or under autopilot for allowed risks |
| coding CLIs (`claude`, `codex`, `omp`, `opencode`) | the project's `config.yaml` `clis`, started by `swe-cli delegate` | yes, in a worktree | no |
| agents: cli, model, reasoning | `agents` | yes, in a worktree | no |
| who reviews | the `reviewer-junior` or `reviewer-senior` agent | — | — |
| session launcher | `launcher` (`tmux` or `orca`) | — | — |
| plugin subagents (`swe:worker`, `swe:adversary`) | `subagents` | inside Claude Code | no |
| the merge gate | `swe-cli merge` | — | the only path to `main` |

### Repositories and worktrees

- A **project is a directory** (`swe-cli project create`; its `project.yaml` lists `repos:`) that holds one or more **central clones**
  (`swe-cli project add <git url>` records and clones one). Each stays on `main`, clean, and nobody edits it.
- **Projects may share a repo.** Two projects can clone the same GitHub repo into their own directories. The
  duplicate is resolved in branches, not by forbidding it: the overlap check also covers every open card of any
  project on the same GitHub repo, and a branch name is used once.
- One **worktree per card** at `<project dir>/.wt/<repo>/<branch>`, created from `origin/main` after a fetch that
  must succeed. The base SHA is recorded. Many agents work at once without sharing a checkout.
- With launcher `orca`, `swe-cli project sync` registers the clones in Orca, so the worktrees and the card terminals
  show up in its UI.
- `swe-cli delegate cleanup` removes the worktree and branch after the PR merges.

### Keeping conflicts small

1. **Cards declare their files** (`--files`). `swe-cli delegate start` refuses a card whose files overlap an open card,
   or that touches a **hotspot** (`hotspots:` in `projects.yaml`: migrations, lockfiles, generated clients, route
   registries) another open card holds. The manager waits for the merge instead of running both.
2. **Small cards** (about 400 changed lines, one feature function) on short-lived branches.
3. **Re-sync at fixed points:** at the start (fetch, then branch from `origin/main`), before the PR
   (`swe-cli delegate sync-branch --verify`: fetch, rebase, `make verify`) and at the merge (`swe-cli merge` refuses a
   branch that is behind or in conflict with `main`).
4. **Conflicts go to a person:** `sync-branch` aborts the rebase, leaves the branch unchanged and names the files.
5. Git sees text conflicts only; `make verify` after the rebase is what catches behaviour conflicts.

### Flows

1. **Request → project.** You start the project's orchestrator (`swe-cli orchestrate <project>`) and tell it the goal.
2. **Plan.** The orchestrator reads `ARCHITECTURE.md`, splits the goal into one GitHub issue per feature function, stamps
   shared decisions into every brief, and lists each card's files.
3. **Build.** `swe-cli delegate start` makes the worktree and a session, starts the project's CLI with the plugin,
   and hands it the brief (a file, named in one line). The CLI writes tests and code inside the card's files, syncs the branch, makes `make verify`
   pass, opens the PR (`Closes #issue`) and prints `CARD DONE <sha> <pr>` or `CARD BLOCKED <reason>`.
4. **Read.** The orchestrator reads `swe-cli delegate status` (state, commits, files, behind-main, outside-scope files and
   the last pane lines), never the whole session.
5. **Review.** On request, `swe-cli delegate review` starts the other CLI read-only on the same worktree
   (`interrogate`). You can also review, merge and resolve conflicts yourself in a CLI.
6. **Merge.** The gate (`swe-cli merge`) merges only at the verified SHA with every required check green and the branch
   up to date, for a risk class autopilot allows or with the human's approval. Money-path never merges without the human.
7. **Close.** The merge closes the issue and deletes the branch; `swe-cli delegate cleanup` removes the worktree.

### Invariants

- Nobody pushes to `main`; every change is a PR with a passing `verify` check.
- A review covers one SHA. A new push needs a new review.
- Code that breaches the project's layering fails `make verify` (`archcheck`, `lint-imports`).
- A change to `ARCHITECTURE.md` comes with an ADR, in its own reviewed PR, approved by the human.
- Orchestrators never edit repository files; the central clone is never edited.
- Every model is named in exactly one place: the project's `config.yaml`.

## Decisions

| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| A1 | **One orchestrator per project, and it can be any CLI agent** (Claude Code, Codex, oh-my-pi), set in `config.yaml` or per project | a fixed manager product for everyone | the orchestrator is the same skill (`fleet-manager`) on whatever agent you have a login for; a project can be added or removed without touching the others |
| A2 | **Coding CLIs are processes, not profiles:** the orchestrator starts them in sessions, one worktree per card | worker profiles shared by all projects, or per project | a worker profile holds memory that mixes projects; the CLI starts fresh per card and reads only its repo |
| A3 | **Orchestrators split work themselves**  | a global auto-decomposer | it could route a project's work to another project; the orchestrator reads the project's architecture first |
| A4 | **The orchestrator only orchestrates;** docs and repo changes are delegated cards too | let it edit docs directly | one write path (branch → PR → review → gate) for everything in a repo |
| A5 | **The merge is a deterministic gate**, not an agent's judgment | a dedicated "merger" agent | merging needs facts, not judgment: the verified SHA, green required checks, an up-to-date branch, an allowed risk class or a human approval |
| A6 | **One issue per card**, branch `<type>/<issue>-<slug>`, PR `Closes #issue` | cards only | the human sees and steers all work in GitHub; issues survive any run |
| A7 | **The submit rules are enforced** (`pr_lint.py`, `archcheck`, `lint-imports`, the size limit) | rules in prose only | a rule that nothing checks is broken by the first agent in a hurry |
| A8 | **Every agent uses the human's `gh` login** for now | a bot account from day one | simplest to start. Consequence: GitHub can't take an approval from the PR's own author, so required approvals are 0 and the gate enforces the review. Move to a bot account, then `setup_repo.sh --approvals 1`. |
| A9 | **Sessions are named terminals you can attach to, send keys to and read:** tmux by default, or Orca terminals (`launcher: orca`) | headless `-p` runs only | the orchestrator can drive them, you can watch and take over (in tmux, or in the Orca UI next to the worktrees). `swe-cli lane` keeps the headless one-shot mode for scripts |
| A10 | **A fetch that fails stops the delegation** | continue from the local `origin/main` | a stale base is worse than no work; `swe-cli doctor` finds the credentials problem first |
| A11 | **A project is a directory of repos; duplicates across projects are solved in branches** | one repo per project, or a global registry of repos | real work spans several repos, and the same repo can serve two products. The overlap check and unique branch names keep their cards apart |

## Risks

| Risk | How we would notice | Mitigation |
|---|---|---|
| an orchestrator works outside its project | a card or PR in another project's repo | the brief names the one project directory |
| the shared `gh` token is too powerful (admin bypass) | a merge without the gate | `enforce_admins` on `main`; `swe-cli merge` is the documented path; a bot account with no admin rights is the fix |
| one subscription runs out | `swe-cli delegate status` shows a stuck or blocked session | the orchestrator reports it and asks; switch the project's CLI (any of Claude Code, Codex, oh-my-pi) or wait.|
| two cards change the same behaviour in different files | green separately, red together | `sync-branch --verify` and the gate's up-to-date rule; serialize cards that depend on each other |
| `ARCHITECTURE.md` drifts from the code | `archcheck` / `lint-imports` green while the doc says otherwise | the manager's weekly status checks the doc against the layering checks; changes need an ADR |
| a self-review is weak | defects found after merge | review for risky cards; the human samples merged PRs; autopilot stays off until 20 clean merges (runbook 3) |
| a session hangs or exits | `swe-cli delegate status` says stopped or unchanged | tmux `remain-on-exit` keeps the last output; `send` a nudge or `stop` and restart the card |

## Plugin decisions

How the plugin and the repository are built (the table above covers the agents).

| # | Decision | Why |
|---|---|---|
| D1 | We own the plugin and install no upstream plugin. | Our format (router + references + tested assets), our domain, our harnesses. It grows from our stack and requirements, not from upstream changes. |
| D2 | The plugin's name comes from the build (`PLUGIN_NAME`, default `swe`). The router skill carries the same name, so the entry command is `/<name>`. | One source, any name. Claude Code accepts a plugin skill named like its plugin as `/<name>` (tested). |
| D3 | Org values are build settings (`PLUGIN_DOMAIN`, `PLUGIN_OWNER`, `PLUGIN_HOMEPAGE`); private ones live in `plugin.local.env`. No org name in tracked files (a test enforces it). | The plugin can be published or shared without leaking internal names. |
| D4 | Skills are flat and grouped by `metadata.group`. | The installers and the Agent Skills spec need `skills/<name>/SKILL.md`. |
| D5 | Skills and roles name agents (`developer`, `documenter`, ...), never models. An agent is a cli, a model and a reasoning level, defined in the project's `config.yaml`. | A new model is one edit (`swe-cli models set`) plus `swe-cli models check`. |
| D6 | Four coding CLIs: Claude Code (Claude models), Codex (OpenAI models), oh-my-pi (OpenAI and Google models) and opencode (any provider). Each agent names its own cli; another family reviews. | Cross-family review is available when it matters; every subscription you hold is used. |
| D7 | The manager is any CLI agent, started by `swe-cli orchestrate` or by opening a terminal in the project directory. The coding CLIs are never profiles. | A profile per CLI held memory that mixed projects. |
| D8 | The manager answers questions with the read-only skills and routes work: it picks a workflow and starts it; it does not code. Judgment lives in the coding CLIs, whose agent is chosen per role or card. | The coordinator's tokens stay a small share, and the project survives any one subscription running out. |
| D9 | "Done" means `make verify` exits 0 on the committed head, and, required CI is green on the PR head. | Verification before parallelism. |
| D10 | Money-path (orders, fills, positions, balances, risk, P&L) goes to the strong agent, is reviewed, replay-tested, and never auto-merged (`swe-cli merge` refuses it). | A wrong answer there is a loss. |
| D11 | Merging is a deterministic gate (`swe-cli merge`), run by the orchestrator under autopilot or with the human's approval; there is no merging agent. | Merging needs facts (verified SHA, green checks, allowed risk or approval), not judgment. |
| D12 | Git and GitHub follow one way (the `github` skill): issue → branch → small Conventional Commits → PR → gate → main; `pr_lint.py`, `archcheck` and `lint-imports` enforce the submit rules. | A rule nothing checks gets broken. |
