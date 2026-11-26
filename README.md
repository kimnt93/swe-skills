# swe-skills

A software-engineering plugin for coding agents. One entry command (`/swe`) picks the language for the job, routes the task to a
structured playbook, the engineering principles, and tested skills, and does not finish until the project's `make verify` passes.
Workflows are defined as repeatable **playbooks** (`/swe:playbook-<name>`), configured via `config.json`, and implementation cards are delegated to worker agents via **Orca CLI sessions**, **T3 Code threads**, or direct headless CLI relays using `/swe:delegate`.

| The job | Language |
|---|---|
| HTTP APIs, services, Kafka consumers | **Go**, Fiber v3 (default) |
| ML, data pipelines (Pathway, Dagster) | **Python** |
| hot paths, Rust cores for Python | **Rust** |
| web apps and dashboards | **Next.js**, or **Vite + React + TypeScript** |

The full stack is in [STACK.md](STACK.md).

## Quick Install

Install across all detected AI agent harnesses with one command:

```bash
curl -fsSL https://raw.githubusercontent.com/kimnt93/swe-skills/main/install.sh | bash
```

Or install from local source:

```bash
git clone https://github.com/kimnt93/swe-skills.git && cd swe-skills
./install.sh
# or via Makefile
make install
make cli
```

## Use

### 1. Playbooks (`/swe:playbook-<name>`)

Exactly three CTO pipelines. `plan` ends at an accepted plan on the issue; `review` and `quick` end at the reviewer/gate merge.

```text
/swe:playbook-plan users cannot export the orders they filtered; plan it
/swe:playbook-review harden the order retry path; review every finding before merge
/swe:playbook-quick fix the typo in docs/README.md and merge it
```

| Playbook | Purpose |
|---|---|
| `/swe:playbook-plan` | CTO card → architect plan comment → back to the CTO → accepts → stop ([example](src/skills/playbook-plan/references/example.md)) |
| `/swe:playbook-review` | Build an accepted plan: PRs → reviewer PASS/FAIL and fix round → merge |
| `/swe:playbook-quick` | CTO issue → developer PR → reviewer/gate merge; docs, small fixes, no planning |
| `/swe:playbook` | Dispatcher and the three-pipeline choice |

### Templates: one style, yours to change

Issues, plans, pull request bodies and PR comments each follow a Markdown template that the linters read. Edit the file
to change the style: [the list and how](src/skills/write-issue/references/templates.md).

### 2. Multi-Agent Delegation (`/swe:delegate`)

Delegate coding tasks to standalone CLI agents via **Orca sessions**, **T3 Code threads**, or direct headless CLI relays:

```text
/swe:delegate codex: implement table view pagination
/swe:delegate claude --model claude-3-7-sonnet --reasoning high: refactor authentication
/swe:delegate fix the race condition in cache eviction
```

### 3. Simplified CLI (`swe-cli`)

```bash
swe-cli update        # update latest code, rebuild plugin, and reinstall into harnesses
swe-cli playbooks     # list all available playbooks and their slash commands
swe-cli delegate      # run delegation runner directly from terminal
swe-cli config show   # inspect active configuration (config.json)
swe-cli doctor        # health check for agent CLIs, Orca, T3 Code, git, gh
```

## Configuration (`config.json`)

Configuration is managed in `config.json` (search paths: `$SWE_CONFIG` -> `./config.json` -> installed plugin directory -> `~/.config/swe/config.json`):

```json
{
  "default_agent": "codex",
  "delegation": {
    "engine": "auto",
    "timeout_ms": 300000,
    "yolo": true
  },
  "orca": { "enabled": true, "binary": "orca" },
  "t3": { "enabled": true, "binary": "t3" },
  "agents": {
    "developer-junior": { "cli": "codex", "model": "o3-mini", "reasoning": "medium" },
    "developer-senior": { "cli": "claude", "model": "claude-sonnet-5-5", "reasoning": "high" },
    "reviewer": { "cli": "claude", "model": "claude-sonnet-5-5", "reasoning": "high" }
  }
}
```

## Documentation

| Read | When |
|---|---|
| [docs/getting-started.md](docs/getting-started.md) | install, first task, troubleshooting |
| [docs/usage.md](docs/usage.md) | what to say for each kind of task |
| [docs/skills/](docs/skills/README.md) | each skill in detail |
| [docs/harnesses.md](docs/harnesses.md) | every supported harness and how it installs |
| [docs/development.md](docs/development.md) | make targets, build settings, layout, enforced rules |
| [cli/README.md](cli/README.md) | every `swe-cli` command |
