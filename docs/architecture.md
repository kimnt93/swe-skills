# Architecture: the swe-skills fleet

How the plugin and its agents run several software projects on Hermes Agent, with GitHub as the
place where all code lands. Written in the `architect` skill's rationale shape: usage first, then
the shape, then the decisions and what was rejected.

## Usage

What the human types, and what happens:

```text
(Telegram / Slack / CLI to the root profile)
"orders: add an endpoint to cancel an open order, and a Cancel button on the dashboard"

root           → routes it to project "orders": a card on board "orders", assigned to pm-orders
pm-orders      → reads ARCHITECTURE.md; creates issues #41 (API) and #42 (UI); two cards:
                 #41 → lane claude, tier mid, risk money-path, may write internal/orders/**
                 #42 → lane omp,    tier mid, risk standard,   may write web/src/orders/**, after #41
claude lane    → Claude Code (/swe) in a worktree on feat/41-cancel-order: test first, code,
                 make verify, PR "feat(orders): cancel an open order" (Closes #41), pr_lint clean
omp lane       → reviews #41's PR with gpt-6-sol: re-runs make verify, interrogates the diff,
                 posts "Verdict: PASS at <sha>"; fleet merge refuses (money-path) → waits for the human
human          → "merge #41"
pm-orders      → fleet merge 41 --approved --sha <sha> → squash-merged, issue closed, branch deleted
                 → card #42 unblocks; the same loop for the dashboard
```

## Shape

```
                    ┌────────────────────────── Hermes Agent (one host) ──────────────────────────┐
 human ──chat──►    │  root (default)       fleet-admin, github      routes requests, manages     │
                    │                                                 projects and profiles       │
                    │      │ card on the project's board                                           │
                    │      ▼                                                                       │
                    │  pm-<project>  ×N     fleet-manager, project,   one per project: issues,     │
                    │  (orchestrators)      github                    cards, docs and repo upkeep  │
                    │      │ cards (issue · risk · tier · may write · decisions · evidence)        │
                    │      ▼                                                                       │
                    │  claude lane ◄──────── review each other ────────► omp lane                  │
                    │  fleet-worker, github                         fleet-worker, github           │
                    │      │ fleet lane run / review                     │                         │
                    └──────┼─────────────────────────────────────────────┼─────────────────────────┘
                           ▼                                             ▼
                 Claude Code + the swe plugin                  oh-my-pi + the swe plugin
                 (opus / sonnet / haiku by tier)               (gpt-6-sol / gemini-3.8-flash by tier)
                           │ git worktree per card, branch <type>/<issue>-<slug>
                           ▼
                 GitHub: PR → required check "verify" → fleet merge (the gate) → main
```

| Piece | Where it is defined | Writes code? | Merges? |
|---|---|---|---|
| root profile (`default`) | `fleet/models.yaml` `board.root` | no | no |
| project managers (`pm-<project>`) | `board.manager` template × `fleet/projects.yaml` | no | only with the human's approval (`fleet merge --approved`) |
| lanes (`claude`, `omp`) | `fleet/models.yaml` `lanes` | through their CLI, in a worktree | as reviewer, through the gate, when autopilot allows the risk |
| worker models per tier | `workers` | — | — |
| who reviews whom | `reviewers` | — | — |
| plugin subagents (`swe:worker`, `swe:adversary`) | `subagents` | inside Claude Code | no |
| the merge gate | `fleet merge` | — | the only path to `main` |

### Flows

1. **Request → project.** The root profile matches the request to a project and creates one card on
   its board, assigned to the manager. Fleet requests (new project, model change) stay with the root.
2. **Plan.** The manager reads `ARCHITECTURE.md`, splits the goal into one GitHub issue and one card
   per feature function, stamps shared decisions into every card, and links dependencies.
3. **Build.** The dispatcher spawns the card's lane in a worktree of the project's repo. The lane runs
   its CLI with the plugin; the CLI writes tests and code inside the card's scope; `make verify` must
   pass; the lane lints and opens the PR (`Closes #issue`).
4. **Review.** Hermes moves the card to review on the other lane, which re-runs `make verify`,
   interrogates the diff with the other model family, checks the submit rules, and posts a verdict
   for one head SHA.
5. **Merge.** The gate (`fleet merge`) merges only at the verified SHA with every required check
   green, and only for a risk class autopilot allows, or with the human's approval. Money-path never
   merges without the human.
6. **Close.** The merge closes the issue and deletes the branch; the manager checks `main`'s CI and
   closes the card's goal when every child is done.

### Invariants

- Nobody pushes to `main`; every change is a PR with a passing `verify` check.
- A review is by the other model family than the author's, and covers one SHA.
- Code that breaches the project's layering fails `make verify` (`archcheck`, `lint-imports`).
- A change to `ARCHITECTURE.md` comes with an ADR, in its own reviewed PR, approved by the human.
- Managers and the root never edit repository files.
- Every model is named in exactly one place: `fleet/models.yaml`.

## Decisions

| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| A1 | **One manager profile per project**, plus a root profile for the fleet | one chef for every project | a manager's memory, skills and descriptions stay about one product; a project can be added or removed without touching the others |
| A2 | **Lanes shared by all projects** | lanes per project (`claude-orders`, `omp-orders`, ...) | lanes hold no project state (each card carries its brief and worktree); per-project lanes multiply profiles without changing behaviour; per-lane limits match subscriptions, which are shared anyway |
| A3 | **Managers split work themselves** (`kanban.auto_decompose: false`, `orchestrator_profile: ""`) | Hermes' built-in auto-decomposer | the decomposer sees every profile and has one global orchestrator, so it could route a project's work to another project's manager; the manager reads the project's architecture first |
| A4 | **The manager only orchestrates;** docs and repo changes are cards | let the manager edit docs directly | one write path (branch → PR → review → gate) for everything in a repo |
| A5 | **The merge is a deterministic gate**, not an agent's judgment | a dedicated "merger" agent | merging needs facts, not judgment: the verified SHA, green required checks, an allowed risk class or a human approval. The review lane runs the gate; the manager runs it with `--approved`. |
| A6 | **One issue per card**, branch `<type>/<issue>-<slug>`, PR `Closes #issue` | cards only | the human sees and steers all work in GitHub; issues survive the board |
| A7 | **The submit rules are enforced** (`pr_lint.py`, `archcheck`, `lint-imports`, the size limit) | rules in prose only | a rule that nothing checks is broken by the first agent in a hurry |
| A8 | **Every agent uses the human's `gh` login** for now | a bot account from day one | simplest to start. Consequence: GitHub can't take an approval from the PR's own author, so required approvals are 0 and the gate enforces the review. Move to a bot account, then `setup_repo.sh --approvals 1`. |

## Risks

| Risk | How we would notice | Mitigation |
|---|---|---|
| a manager routes work outside its project | a card on another board, a PR in another repo | descriptions name the one project; boards are isolated; root routes by project name |
| the shared `gh` token is too powerful (admin bypass) | a merge without the gate | `enforce_admins` on `main`; `fleet merge` is the documented path; a bot account with no admin rights is the fix |
| lanes overload one subscription | rate-limit errors, `respawn_guarded` events | `kanban.max_in_progress_per_profile`; spread cards across lanes |
| `ARCHITECTURE.md` drifts from the code | `archcheck` / `lint-imports` green while the doc says otherwise | the manager's weekly status checks the doc against the layering checks; changes need an ADR |
| a lane's review is weak | defects found after merge | the human samples merged PRs; autopilot stays off until 20 clean merges (runbook 3) |

## Plugin decisions

How the plugin and the repository are built (the table above covers the fleet).

| # | Decision | Why |
|---|---|---|
| D1 | We fork pstack's ideas into our own plugin; we don't install pstack. | Our format (router + references + tested assets), our domain, our harnesses. `UPSTREAM` + `make upstream` keep us able to take improvements. |
| D2 | The plugin's name comes from the build (`PLUGIN_NAME`, default `swe`). The router skill carries the same name, so the entry command is `/<name>`. | One source, any name. Claude Code accepts a plugin skill named like its plugin as `/<name>` (tested). |
| D3 | Org values are build settings (`PLUGIN_DOMAIN`, `PLUGIN_OWNER`, `PLUGIN_HOMEPAGE`); private ones live in `plugin.local.env`. No org name in tracked files (a test enforces it). | The plugin can be published or shared without leaking internal names. |
| D4 | Skills are flat and grouped by `metadata.group`. | The installers and the Agent Skills spec need `skills/<name>/SKILL.md`. |
| D5 | Skills name tiers (`top`, `mid`, `low`), never models. Every agent and model lives in `fleet/models.yaml`. | A new model is one edit plus `fleet models apply`. |
| D6 | Two coding lanes: `claude` (Claude models) and `omp` (OpenAI and Google models). Each reviews the other. | Cross-family review comes free; two subscriptions are used. |
| D7 | Hermes profiles: the root `default` (fleet admin and router), one `pm-<project>` manager per project (orchestrator only), and the shared lanes `claude` and `omp`. Scout, reviewer and reconciler are cards, not profiles. | A profile only for a different scope, tools, permissions or rate limits. |
| D8 | Managers run on a judgment model (Sonnet 5.5; Opus pinned per card for money-path) and split work themselves (auto-decompose off). The root and the lane brains are cheap. | Card quality spreads to every worker; coordinator tokens are a small share. |
| D9 | "Done" means `make verify` exits 0 on the committed head, and, on the board, required CI is green on the PR head. | Verification before parallelism. |
| D10 | Money-path (orders, fills, positions, balances, risk, P&L) is top tier, cross-family reviewed, replay-tested, and never auto-merged (`fleet merge` refuses it). | A wrong answer there is a loss. |
| D11 | Merging is a deterministic gate (`fleet merge`), run by the review lane under autopilot or by the manager with the human's approval; there is no merging agent. | Merging needs facts (verified SHA, green checks, allowed risk or approval), not judgment. |
| D12 | Git and GitHub follow one way (the `github` skill): issue → branch → small Conventional Commits → PR → gate → main; `pr_lint.py`, `archcheck` and `lint-imports` enforce the submit rules. | A rule nothing checks gets broken. |
