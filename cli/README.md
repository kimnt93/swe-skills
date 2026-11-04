# swe-cli (`<plugin>-cli`)

Runs the plugin's agents: a project is a directory of repo clones listed in `project.yaml`, its orchestrator is any CLI agent
(Claude Code, Codex, oh-my-pi), and Hermes Kanban is optional (`board.enabled`). **Every agent, at every level, and the model it uses
is set in one file, `models.yaml`.** The command reads it. `make cli` links it as `<plugin>-cli`; `swe-cli init` makes a directory a project; workflows are in `workflows/`, roles in `roles.yaml` ([docs/workflows.md](../docs/workflows.md)).

| Level | Agents | Writes code? | Default model |
|---|---|---|---|
| orchestrator | any CLI agent started in the project directory (`swe-cli orchestrate`); `orchestrator:` in `models.yaml`, per project override | no | claude, tier mid |
| board (optional) | Hermes `root` and one `pm-<project>` manager per project, when `board.enabled: true` | no | Gemini 3.8 Flash (Claude cannot be the Hermes orchestrator) |
| CLIs | `claude`, `codex`, `omp`: the coding CLIs the orchestrator starts in worktrees (`swe-cli delegate`); not Hermes profiles | yes | — |
| workers | the model a CLI runs, per tier `top` / `mid` / `low` | yes | claude: opus / sonnet / haiku; codex: gpt-6-sol; omp: gpt-6-sol high / medium, Gemini 3.8 Flash |
| reviewers | which CLI reviews work written with each CLI, at which tier | no | Claude work → omp top; codex work → claude top; omp work → claude mid |
| subagents | `<plugin>:worker`, `<plugin>:adversary` shipped in the Claude Code plugin | yes / no | the claude mid / top worker |
| omp roles | omp's own internal subagents | — | Gemini 3.8 Flash, gpt-6-sol |

`models.yaml` also holds the board settings (`kanban:`) and the autopilot switch
(`autopilot.auto_merge`, empty until you trust a risk class).

## The command

```bash
swe-cli models show                 # every agent, its level and its model
swe-cli models check                # each model exists where it runs, each provider is logged in
swe-cli models apply [--dry-run]    # push models.yaml to the Hermes profiles and to omp
swe-cli init [dir] [--repo url]...   # make a directory a project: AGENTS.md, workflows, roles, models, project.yaml; asks for git URLs
swe-cli update [harness ...]        # git pull main, make install (or the named harnesses), relink the command
swe-cli project update [--force]    # refresh this project's AGENTS.md, workflows, roles, models, learn skill
swe-cli project add <git url>       # add a repo to this project's project.yaml and clone it
swe-cli project list|sync           # the projects; clone what is missing, Orca registration; with Hermes a manager and board
swe-cli flow run|status|retry|merge|clean|stop|list|validate|graph   # YAML workflows, one agent per node
swe-cli orchestrate <project>       # start the project's orchestrator (any CLI) in its directory
swe-cli bootstrap                   # projects, models, context; with Hermes also root and managers
swe-cli sync                        # Hermes: share the root's login and keys, apply models and context to every profile (/sync)
swe-cli context show|apply          # context window and compaction point per tool; write Claude Code, Codex, omp
swe-cli doctor [project]            # git credentials, tmux or Orca, CLIs, gh, each central clone
swe-cli delegate start|status|send|review|scope|sync-branch|stop|cleanup   # coding CLIs in worktrees (docs/delegation.md)
swe-cli lane run <cli> <tier> <card> | swe-cli lane review <author-cli> <card>   # headless one-shot
swe-cli merge <pr> --risk <r> --sha <verified sha> [--approved]   # the merge gate
swe-cli name                        # the plugin name
```

`swe-cli merge` merges only when the PR is open, its head is the SHA the reviewer verified, and every
required check passed, and either the card's risk class is in `autopilot.auto_merge` (never
money-path) or the human approved (`--approved`, run by the project's orchestrator). It refuses a PR with
no required checks. The design is in `docs/architecture.md`; the per-agent skills in
`docs/agents-and-skills.md`.

## Setup

```bash
make cli
bash cli/tests/selftest.sh            # fakes (CLIs, gh, Orca), a scratch repo: nothing live is touched
claude auth login; codex login; omp login openai-codex      # the CLIs you use
swe-cli models check                      # pick exact ids with `omp models ls` if it complains
swe-cli project add orders --dir ~/work/orders --repo api=acme/orders-api --repo web=acme/orders-web
swe-cli doctor orders                     # 0 problems
swe-cli orchestrate orders                # the orchestrator, in ~/work/orders
# optional Hermes: board.enabled: true in models.yaml, hermes auth add gemini, swe-cli bootstrap, hermes gateway restart
```

## A new model (say Opus 6)

```bash
claude update                                     # aliases opus/sonnet/haiku now mean the newest
$EDITOR cli/models.yaml                         # only where you pin ids, or to move an agent
swe-cli models check && swe-cli models apply          # omp (and Hermes profiles, if enabled) updated
make claude                                       # rebuild the plugin so its subagents follow
swe-cli models show
```

Workers and reviewers need no apply: `swe-cli delegate` and `swe-cli lane` read `models.yaml` on every card.
