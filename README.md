# swe-skills

A software-engineering plugin for coding agents. One entry command (`/swe`) picks the language for the job, routes the task to a
playbook, the engineering principles and tested skills, and does not finish until the project's `make verify` passes.
On top of the skills, `swe-cli` runs a **project of agents**: a directory with your repos, where a manager agent turns a request into
a workflow run (plan, build, check, review, merge) with one agent per node.

| The job | Language |
|---|---|
| HTTP APIs, services, Kafka consumers | **Go**, Fiber v3 (default) |
| ML, data pipelines (Pathway, Dagster) | **Python** |
| hot paths, Rust cores for Python | **Rust** |
| web apps and dashboards | **Next.js**, or **Vite + React + TypeScript** |

The full stack is in [STACK.md](STACK.md).

## Setup

```bash
git clone <this repo> && cd swe-skills
make install            # build, validate, install into every harness found on this machine
make claude codex omp   # or only some harnesses (make harness lists all 55)
make cli                # link the swe-cli command into ~/.local/bin
```

## Use

```text
/swe the orders consumer double-counts fills when Kafka redelivers. repro first, then fix and verify.
/swe:interrogate review this branch
```

| Harness | Entry | Another skill |
|---|---|---|
| Claude Code | `/swe` | `/swe:<skill>` |
| Codex | `$swe:swe` | `$swe:<skill>` |
| oh-my-pi | `/skill:swe` | `/skill:<skill>` |
| any other harness | skill `swe` | skill `swe-<skill>` |

## A project of agents

```bash
mkdir orders && cd orders
swe-cli project create orders          # asks: project manager (pm) or developer (dev); --mode pm|dev skips the question
cd orders && swe-cli project orders add <git url>   # add repos one at a time; `swe-cli project init` makes the current directory a project
swe-cli orchestrate orders    # start the manager (any harness) in this directory, then ask it for work
swe-cli update                # later: pull main, reinstall everywhere; `swe-cli project update` refreshes this project
```

Agents (`cli`, `model`, `reasoning`) are defined in one file, the project's `config.yaml`; the manager is an agent too. How workflows,
roles, reports, change logs and merging work: [docs/workflows.md](docs/workflows.md).

## Examples

[examples/pm-jlogger](examples/pm-jlogger/README.md) (a project manager runs plan, build, review, merge) and
[examples/dev-gorouter](examples/dev-gorouter/README.md) (a developer's agent: issue, code, PR; no review, no merge).

## Documentation

| Read | When |
|---|---|
| [docs/getting-started.md](docs/getting-started.md) | install, first task, troubleshooting |
| [docs/usage.md](docs/usage.md) | what to say for each kind of task |
| [docs/workflows.md](docs/workflows.md) | the project directory, workflows, roles, merge and clean |
| [docs/architecture.md](docs/architecture.md) | the design: roles, flows, invariants, decisions |
| [docs/agents-and-skills.md](docs/agents-and-skills.md) | which agent gets which skills |
| [docs/skills/](docs/skills/README.md) | each skill in detail |
| [docs/harnesses.md](docs/harnesses.md) | every supported harness and how it installs |
| [docs/context.md](docs/context.md) | context limits per tool |
| [docs/recommended-setup.md](docs/recommended-setup.md) | order of work, agents, the daily routine |
| [docs/development.md](docs/development.md) | make targets, build settings, layout, enforced rules |
| [cli/README.md](cli/README.md) | every `swe-cli` command |
