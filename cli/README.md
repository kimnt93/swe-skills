# swe-cli (`<plugin>-cli`)

Runs the plugin's agents: a project is a directory of repo clones listed in `project.yaml`, its manager is any CLI agent
(Claude Code, Codex, oh-my-pi, opencode). **Every agent, its harness (cli), model and reasoning level, is set in one file, the project's `config.yaml`**
(template: `cli/templates/config.yaml`; `swe-cli init` copies it into the project). The command reads it. `make cli` links it as `<plugin>-cli`; `swe-cli init` makes a directory a project; workflows are in `workflows/`, roles in the `roles:` block of `config.yaml` ([docs/workflows.md](../docs/workflows.md)).

An agent is three fields: `cli` (`claude`, `codex`, `omp` or `opencode`), `model` and `reasoning`. A role in the `roles:` block of `config.yaml` names its agent;
a node or a planner card may name another or override one field.

| Level | What | Default |
|---|---|---|
| manager | the agent you talk to in the project directory (`swe-cli orchestrate`); `manager:` in `config.yaml`, `manager:` in `project.yaml` per project | claude sonnet, high |
| agents | `planner` (opus), `developer-junior` (haiku, high), `developer-senior` (sonnet, high), `reviewer-junior` (haiku, high), `reviewer-senior` (sonnet, medium), `documenter` (omp gemini flash), `scribe`, `ci-fixer`, `integrator`, `verifier`: `{cli, model, reasoning}` | only the planner needs the strongest model |
| roles | `roles:` in `config.yaml`: the skills and the agent of each workflow role | planner, developer, documenter, reviewer, ci-fixer, scribe, verifier, integrator |
| mode | `mode:` in `config.yaml`: `pm` (all workflows, review and merge) or `dev` (the `task` workflow: issue, code, PR) | pm |

Harness launch settings (permissions, the prompt text the runner waits for) are built in; a `clis:` block in `config.yaml` overrides them.

Reasoning is passed the harness's own way and left out when empty: `claude --effort`, `codex -c model_reasoning_effort`,
`omp --thinking`, `opencode --variant` (headless) or the `variant` of its `build` agent (interactive).

`config.yaml` also holds the context policy and the autopilot switch
(`autopilot.auto_merge`, empty until you trust a risk class).

## The command

```bash
swe-cli models show                 # every agent: its cli, model and reasoning
swe-cli models set <agent> --cli C --model M --reasoning R   # change one agent (comments in the file stay)
swe-cli models check                # each model exists where it runs, each provider is logged in
swe-cli models apply [--dry-run]    # write omp's model roles
swe-cli project init [dir]         # make a directory (default: here) a project: AGENTS.md, workflows, roles, models, project.yaml
swe-cli project create <project>   # make ./<project>/ and init it
swe-cli project <project> add <git url>   # add a repo to that project and clone it (no repos on init)
swe-cli update [harness ...]        # git pull main, make install (or the named harnesses), relink the command
swe-cli project update [--force]    # refresh this project's AGENTS.md, workflows, roles, models, learn skill
swe-cli project list|sync           # the projects; clone what is missing, Orca registration
swe-cli flow run|status|retry|merge|clean|stop|list|validate|graph   # YAML workflows, one agent per node
swe-cli orchestrate <project>       # start the project's manager (any CLI) in its directory
swe-cli bootstrap                   # clone repos, apply models and context
swe-cli context show|apply          # context window and compaction point per tool; write Claude Code, Codex, omp
swe-cli doctor [project]            # git credentials, tmux or Orca, CLIs, gh, each central clone
swe-cli delegate start|status|send|review|scope|sync-branch|stop|cleanup   # coding CLIs in worktrees (docs/delegation.md)
swe-cli lane run <agent> <card> | swe-cli lane review <author-cli> <card> [agent]   # headless one-shot
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
```

## A new model (say Opus 6)

```bash
claude update                                     # aliases opus/sonnet/haiku now mean the newest
$EDITOR config.yaml                             # in the project directory; only where you pin ids, or to move an agent
swe-cli models check && swe-cli models apply          # omp updated
make claude                                       # rebuild the plugin so its subagents follow
swe-cli models show
```

Workers and reviewers need no apply: `swe-cli delegate` and `swe-cli lane` read `config.yaml` on every card.
