# 00 — architecture

status: reference

## The system

The full design (usage, shape, flows, invariants, decisions, risks) is in
[`docs/architecture.md`](../docs/architecture.md); the per-agent skills and tools in
[`docs/agents-and-skills.md`](../docs/agents-and-skills.md). In one picture:

```
 human ─► root (default): routes the request ─► pm-<project>: issues + cards (reads ARCHITECTURE.md)
                                                     │
                       ┌─────────────────────────────┴─────────────────────────────┐
                       ▼                                                           ▼
          lane claude → Claude Code + /<plugin>                       lane omp → oh-my-pi + /skill:<plugin>
                       │ branch <type>/<issue>-<slug> → PR (Closes #issue) → make verify
                       └──────────── review by the other lane, verdict for one SHA ─┘
                                                     │
                     fleet merge (the gate): allowed risk or the human's approval, verified SHA, green checks
                                                     ▼
                                    main · issue closed · branch deleted · sampled by the human
```

## Decisions (change one only by editing this file in its own commit)

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
| D11 | Merging is a deterministic gate (`fleet merge`), run by the review lane under autopilot or by the manager with the human's approval; there is no merging agent. | Merging needs facts (verified SHA, green checks, allowed risk or approval), not judgment. |
| D12 | Git and GitHub follow one way (the `github` skill): issue → branch → small Conventional Commits → PR → gate → main; `pr_lint.py`, `archcheck` and `lint-imports` enforce the submit rules. | A rule nothing checks gets broken. |
| D10 | Money-path (orders, fills, positions, balances, risk, P&L) is top tier, cross-family reviewed, replay-tested, and never auto-merged (`fleet merge` refuses it). | A wrong answer there is a loss. |

## Map

| Path | Role |
|---|---|
| `src/skills/router` | becomes `/<plugin>`: playbooks, tiers (`models`), `harness` map, reply rules, generated index |
| `src/skills/principles` | 19 forked principles + `money-path` |
| `src/skills/{tdd,architect,interrogate,blast-radius,benchmark-checklist,correct,verify-create,verify-maintain,replay-test,formal-verify,ketchup,reflect}` | process and proof |
| `src/skills/{go,py,rust}-code`, `db-*`, `api-contract`, `deployment-setup`, `service-*`, `data-realtime-metrics` | domain skills |
| `src/agents` | Claude Code subagents `<plugin>:worker`, `<plugin>:adversary` |
| `fleet/` | `models.yaml`, `projects.yaml`, `bin/fleet`, `bin/fleet-lane`, `skills/fleet-admin`, `skills/fleet-manager`, `skills/fleet-worker` |
| `docs/` | `architecture.md` (the solution design), `agents-and-skills.md` (the recommended setup) |
