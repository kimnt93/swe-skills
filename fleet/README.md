# fleet

Runs the plugin's agents: a project is a directory of repo clones, its orchestrator is any CLI agent
(Claude Code, Codex, oh-my-pi), and Hermes Kanban is optional (`board.enabled`). **Every agent, at every level, and the model it uses
is set in one file, `models.yaml`.** The `fleet` command reads it.

| Level | Agents | Writes code? | Default model |
|---|---|---|---|
| orchestrator | any CLI agent started in the project directory (`fleet orchestrate`); `orchestrator:` in `models.yaml`, per project override | no | claude, tier mid |
| board (optional) | Hermes `root` and one `pm-<project>` manager per project, when `board.enabled: true` | no | Gemini 3.8 Flash (Claude cannot be the Hermes orchestrator) |
| CLIs | `claude`, `codex`, `omp`: the coding CLIs the orchestrator starts in worktrees (`fleet delegate`); not Hermes profiles | yes | — |
| workers | the model a CLI runs, per tier `top` / `mid` / `low` | yes | claude: opus / sonnet / haiku; codex: gpt-6-sol; omp: gpt-6-sol high / medium, Gemini 3.8 Flash |
| reviewers | which CLI reviews work written with each CLI, at which tier | no | Claude work → omp top; codex work → claude top; omp work → claude mid |
| subagents | `<plugin>:worker`, `<plugin>:adversary` shipped in the Claude Code plugin | yes / no | the claude mid / top worker |
| omp roles | omp's own internal subagents | — | Gemini 3.8 Flash, gpt-6-sol |

`models.yaml` also holds the board settings (`kanban:`) and the autopilot switch
(`autopilot.auto_merge`, empty until you trust a risk class).

## The command

```bash
fleet models show                 # every agent, its level and its model
fleet models check                # each model exists where it runs, each provider is logged in
fleet models apply [--dry-run]    # push models.yaml to the Hermes profiles and to omp
fleet project add|list|sync       # a project directory, its repo clones (cloned if missing), Orca registration; with Hermes a manager and board
fleet orchestrate <project>       # start the project's orchestrator (any CLI) in its directory
fleet bootstrap                   # projects, models, context; with Hermes also root and managers
fleet sync                        # Hermes: share the root's login and keys, apply models and context to every profile (/sync)
fleet context show|apply          # context window and compaction point per tool; write Claude Code, Codex, omp
fleet doctor [project]            # git credentials, tmux or Orca, CLIs, gh, each central clone
fleet delegate start|status|send|review|scope|sync-branch|stop|cleanup   # coding CLIs in worktrees (docs/delegation.md)
fleet lane run <cli> <tier> <card> | fleet lane review <author-cli> <card>   # headless one-shot
fleet merge <pr> --risk <r> --sha <verified sha> [--approved]   # the merge gate
fleet name                        # the plugin name
```

`fleet merge` merges only when the PR is open, its head is the SHA the reviewer verified, and every
required check passed, and either the card's risk class is in `autopilot.auto_merge` (never
money-path) or the human approved (`--approved`, run by the project's orchestrator). It refuses a PR with
no required checks. The design is in `docs/architecture.md`; the per-agent skills in
`docs/agents-and-skills.md`.

## Setup

```bash
ln -sf "$PWD"/fleet/bin/fleet ~/.local/bin/fleet
bash fleet/tests/selftest.sh            # fakes (CLIs, gh, Orca), a scratch repo: nothing live is touched
claude auth login; codex login; omp login openai-codex      # the CLIs you use
fleet models check                      # pick exact ids with `omp models ls` if it complains
fleet project add orders --dir ~/work/orders --repo api=acme/orders-api --repo web=acme/orders-web
fleet doctor orders                     # 0 problems
fleet orchestrate orders                # the orchestrator, in ~/work/orders
# optional Hermes: board.enabled: true in models.yaml, hermes auth add gemini, fleet bootstrap, hermes gateway restart
```

## A new model (say Opus 6)

```bash
claude update                                     # aliases opus/sonnet/haiku now mean the newest
$EDITOR fleet/models.yaml                         # only where you pin ids, or to move an agent
fleet models check && fleet models apply          # omp (and Hermes profiles, if enabled) updated
make claude                                       # rebuild the plugin so its subagents follow
fleet models show
```

Workers and reviewers need no apply: `fleet delegate` and `fleet lane` read `models.yaml` on every card.
