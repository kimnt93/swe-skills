# Workflows

A request becomes a **run** of a workflow: a DAG of nodes in YAML, executed by `swe-cli flow` (`cli/bin/flow`,
one Python file). Every software task follows a flow (plan, build, check, review, merge), so the flow lives in
YAML and the agents only do the steps. The manager (the orchestrator agent) starts runs and merges; it does not
do a node's work.

## A project directory

`swe-cli init` makes a directory a project:

```
orders/
  AGENTS.md          the orchestrator's instructions (read by Claude Code, Codex, oh-my-pi)
  PROJECT.md         stack, dependencies, commands, conventions, gotchas; under 2000 words, kept by the manager
  skills/            the project's own skills; `learn` is created by init, the manager adds topics here
  project.yaml       name, default cli, and the repos: git url, github owner/repo, folder, hotspots
  workflows/*.yaml   this project's copy of the workflows (edit them; they override the bundled ones)
  roles.yaml         the roles (skills, harness, tier, effort); a role here replaces the bundled one
  models.yaml        tier to model per harness, reviewers, orchestrator, launcher
  api/  web/         the repo clones (worktrees of running cards are under .wt/)
```

`swe-cli project add <git url>` (or the orchestrator, when you ask) adds a repo to `project.yaml` and clones it.
The command finds the project from the current directory upward (`project.yaml`), or by name from anywhere
(`~/.swe/workspaces.yaml`, written by `init`).

`swe-cli init <new dir>` creates the directory with these files; `swe-cli init` inside an existing directory adds
them and keeps what is there. `swe-cli project notes` checks `PROJECT.md` against the 2000-word limit.

## Updating

`swe-cli update` pulls the plugin's `main` branch (fast-forward only; it refuses a dirty checkout or another branch),
rebuilds, reinstalls into every detected harness (`swe-cli update claude codex` for chosen ones) and relinks the command.
`swe-cli project update` then brings this project's `AGENTS.md`, `workflows/`, `roles.yaml`, `models.yaml` and
`skills/learn` up to the new versions. A file you did not edit is replaced; one you edited is kept and the new version is
written as `<file>.new` for you to merge (`--force` replaces it after saving `<file>.bak`). `PROJECT.md`,
`project.yaml` and the clones are never touched. The versions it last wrote are remembered in `.swe/shipped.json`.

## Skills per node, and self-improvement

A node's brief tells the agent which `swe` skills to enable (only those of its role, from `roles.yaml`) and to
disable the other `swe` skills. Skills from the agent's system or harness stay available. Every brief says to
read `PROJECT.md` first and lists the project's own skills.

Each agent ends its report with `## Learned`: up to five durable facts. The run report collects them. After the
merge, and before `flow clean`, the manager folds them into `PROJECT.md` with the project's `learn` skill; detail
that would push the file past 2000 words moves into `skills/<topic>/SKILL.md`. Agents never edit `PROJECT.md`
themselves, so parallel nodes cannot collide.

## A workflow

```yaml
name: feature
description: "..."
inputs: {goal: {required: true}, repo: {default: ""}, risk: {default: standard}}
nodes:
  plan:   {role: planner, goal: "Plan this goal ... ${inputs.goal}"}
  cards:  {needs: [plan], map: "${nodes.plan.cards}", workflow: "${item.workflow|card}"}   # one sub-run per card, in parallel
  report: {type: report, needs: [cards], always: true}
```

| Node | Meaning |
|---|---|
| `role: <name>` | an agent: starts one session with the role's skills only, on its harness, model and effort |
| `type: checks` | wait for the PR's required checks; `on_fail: {run: ci-fix, rounds: 2}` runs a fix node and retries |
| `map` + `workflow` | fan out over a list (the plan's cards) into a sub-workflow, in parallel |
| `type: report` | write the run report for the manager |
| `type: shell` | a command, no agent |
| `needs`, `when`, `always`, `manual` | order, a condition, run even after a failure, run only as a fix target |
| `workspace` | `new` own worktree and branch, `same:<node>` reuse that node's worktree, `scratch` read-only, `pr` an open PR's branch |
| `reviews: <node>` | the harness must be another model family than that node's |
| `tier`, `effort`, `harness` | override the role per node |

Values can use `${inputs.x}`, `${item.y|default}` and `${nodes.n.field}`. Shipped: `feature`, `bugfix`, `docs`,
`card` (build, checks, review with fix rounds), `docs-card`, `ci-fix`, `conflict`, `verify`, `changelog`.
`swe-cli flow validate` checks roles, skills, tiers, cycles and `when` expressions; `swe-cli flow graph <wf>` prints
the DAG with each node's harness, tier and effort.

## Roles: the right model for the job

`roles.yaml` decides, per role, the skills, the harness, the tier and the effort. A documenter runs on `low`
(Haiku 5.5 on Claude, gpt-6-luna on Codex, no effort flag); a developer on `mid`; a reviewer on `top`, on another
model family than the developer. Tiers map to models in `models.yaml` (`workers`, `reviewers`).

## Reports, the manager, and cleaning up

Each node writes its report to the run's tmp directory (`$SWE_TMP/swe/<project>/<run>/reports/`, default `/tmp`)
and prints one outcome line (`CARD DONE <sha> <pr>`, `REVIEW DONE <sha> <n> PASS|FAIL`, `NODE DONE <text>`, or
the BLOCKED variants). The runner reads both and starts the next nodes. The last node writes `report.md` for the
manager. Then:

```bash
swe-cli flow merge <project> <run> [--approved]   # the merge gate for each ready PR
swe-cli flow clean <project> <run>                # sessions, worktrees, branches, records, tmp directory
```

## Tiers: one place

Roles and nodes name a **tier** (`top`, `mid`, `low`) and a harness, never a model. The project's `models.yaml` (template:
`cli/templates/models.yaml`, copied by `swe-cli init`, refreshed by `swe-cli project update`) is the only file that says which model
and effort a tier means on each harness, which harness reviews which, the launcher (tmux or Orca), the context policy and the
autopilot switch. A new model is one edit there plus `swe-cli models check`.

## Change logs

The merge gate refuses a PR that needs a `CHANGELOG.md` entry and has none (`docs`, `chore`, `ci`, `test`, `style`, `build`
titles and the `no-changelog` label are exempt). `flow merge` then tells you to run
`swe-cli flow run <project> changelog --input pr=<n> --input repo=<owner/repo>`: a `scribe` agent adds the entry on the PR's
branch, checks run again and a reviewer re-reviews the new head. After each merge `flow merge` appends the PR to
`changelog/<repo>.md` and `changelog/project.md` in the project directory. `swe-cli changelog show --repo <r> --since <date>`
reads them. See the `changelog` skill.

A branch that is behind `main` or conflicts is not merged by force: a reviewer agent updates it, resolves the
conflicts, re-runs the checks and re-reviews, then the merge is retried. After `flow clean` nothing of the run
is left on the machine. Several runs can go at once; cards that touch the same files or a hotspot wait for each
other, also across projects that clone the same repo.
