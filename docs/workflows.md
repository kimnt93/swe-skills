# Workflows

A request becomes a **run** of a workflow: a DAG of nodes in YAML, executed by `swe-cli flow` (`cli/bin/flow`,
one Python file). Every software task follows a flow (plan, build, check, review, merge), so the flow lives in
YAML and the agents only do the steps. The manager (the orchestrator agent) starts runs and merges; it does not
do a node's work.

## A project directory

`swe-cli project init` (here) or `swe-cli project create <name>` (a new directory) makes a project:

```
orders/
  AGENTS.md          the orchestrator's instructions (read by Claude Code, Codex, oh-my-pi)
  PROJECT.md         stack, dependencies, commands, conventions, gotchas; under 2000 words, kept by the manager
  skills/            the project's own skills; `learn` is created by init, the manager adds topics here
  project.yaml       name, default cli, and the repos: git url, github owner/repo, folder, hotspots
  workflows/*.yaml   this project's copy of the workflows (edit them; they override the bundled ones)
  config.yaml        mode (pm or dev), the agents (cli, model, reasoning), the roles (skills, agent), manager, launcher
  api/  web/         the repo clones (worktrees of running cards are under .wt/)
```

`swe-cli project add <git url>` (or the orchestrator, when you ask) adds a repo to `project.yaml` and clones it.
The command finds the project from the current directory upward (`project.yaml`), or by name from anywhere
(`~/.swe/workspaces.yaml`, written by `init`).

`swe-cli project init` asks who works here: a **project manager** (`pm`: plan, build, review, merge: every workflow) or a
**developer** (`dev`: read or create the issue, code, open the PR; only the `task` workflow, no review, no merge). Pass
`--mode pm|dev` to skip the question. `swe-cli project create <name>` creates the directory with these files; `swe-cli project init` inside an existing directory adds
them and keeps what is there. `swe-cli project notes` checks `PROJECT.md` against the 2000-word limit.

## Updating

`swe-cli update` pulls the plugin's `main` branch (fast-forward only; it refuses a dirty checkout or another branch),
rebuilds, reinstalls into every detected harness (`swe-cli update claude codex` for chosen ones) and relinks the command.
`swe-cli project update` then brings this project's `AGENTS.md`, `workflows/`, the `roles:` block of `config.yaml`, `config.yaml` and
`skills/learn` up to the new versions. A file you did not edit is replaced; one you edited is kept and the new version is
written as `<file>.new` for you to merge (`--force` replaces it after saving `<file>.bak`). `PROJECT.md`,
`project.yaml` and the clones are never touched. The versions it last wrote are remembered in `.swe/shipped.json`.

## Skills per node, and self-improvement

A node's brief tells the agent which `swe` skills to enable (only those of its role, from the `roles:` block of `config.yaml`) and to
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
| `role: <name>` | an agent: starts one session with the role's skills only, run by the role's agent (cli, model, reasoning) |
| `type: checks` | wait for the PR's required checks; `on_fail: {run: ci-fix, rounds: 2}` runs a fix node and retries |
| `map` + `workflow` | fan out over a list (the plan's cards) into a sub-workflow, in parallel |
| `type: report` | write the run report for the manager |
| `type: shell` | a command, no agent |
| `needs`, `when`, `always`, `manual` | order, a condition, run even after a failure, run only as a fix target |
| `workspace` | `new` own worktree and branch, `same:<node>` reuse that node's worktree, `scratch` read-only, `pr` an open PR's branch |
| `reviews: <node>` | marks a review node and the node it judges; the review depth follows the agent (`reviewer-junior` fast, `reviewer-senior` deep) |
| `agent`, `cli`, `model`, `reasoning` | override the role's agent per node (`agent:` picks another from `config.yaml`; the others change one field) |

Values can use `${inputs.x}`, `${item.y|default}` and `${nodes.n.field}`. Shipped: `feature`, `bugfix`, `docs`,
`card` (build, checks, review with fix rounds), `docs-card`, `ci-fix`, `conflict`, `verify`, `changelog`.
`swe-cli flow validate` checks roles, skills, agents, cycles and `when` expressions; `swe-cli flow graph <wf>` prints
the DAG with each node's agent, cli, model and reasoning.

## Roles: the right model for the job

the `roles:` block of `config.yaml` decides, per role, the skills and the agent. The default agents: `planner` (the one strong model), `developer-junior` (Haiku, clear cards),
`developer-senior` (Sonnet, medium or complex cards), `reviewer-junior` (a fast check against the issue and the PR),
`reviewer-senior` (a deeper check for complex cards or code the human did not write), `documenter` (omp, Gemini Flash).
The build node runs `developer-junior` and the review node `reviewer-junior`; a planner card names `"agent"` and
`"reviewer"` to go up. Agents are defined in `config.yaml` (`agents`). There is no reviewer map: the reviewer is a role.

## Reports, the manager, and cleaning up

Each node writes its report to the run's tmp directory (`$SWE_TMP/swe/<project>/<run>/reports/`, default `/tmp`)
and prints one outcome line (`CARD DONE <sha> <pr>`, `REVIEW DONE <sha> <n> PASS|FAIL`, `NODE DONE <text>`, or
the BLOCKED variants). The runner reads both and starts the next nodes. The last node writes `report.md` for the
manager. Then:

```bash
swe-cli flow merge <project> <run> [--approved]   # the merge gate for each ready PR
swe-cli flow clean <project> <run>                # sessions, worktrees, branches, records, tmp directory
swe-cli flow run <project> <workflow> --goal T --merge [--approved]   # all of it in one command
```

`--merge` merges through the same gate and cleans when every card passed; without `--approved` the gate still holds
what needs a human (autopilot decides). A run with a failed, blocked or cancelled card ends as `attention` and
`flow merge` merges only the PRs that passed. `flow retry` starts a fresh session in the same worktree for a failed
node and rebuilds the report. Two cards of one run must have disjoint files: a card holds its files until its PR is
merged, so a clash inside a run fails at once, while a clash with another run's open card waits (`lock_wait`).

## Agents: one place

Roles and nodes name an **agent**, never a model. An agent is `{cli, model, reasoning}` with `cli` one of `claude`, `codex`,
`omp`, `opencode`. The project's `config.yaml` (template: `cli/templates/config.yaml`, copied by `swe-cli init`, refreshed by
`swe-cli project update`) is the only file that defines the agents, which agent reviews which author's work, the manager, the
launcher (tmux or Orca), the context policy and the autopilot switch. A new model is one edit there (or
`swe-cli models set <agent> --cli C --model M --reasoning R`) plus `swe-cli models check`.

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
