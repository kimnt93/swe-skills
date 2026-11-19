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

```text
/swe:playbook-deliver implement table view pagination across web and API
/swe:playbook-bugfix the orders consumer double-counts fills when Kafka redelivers. repro first, then fix and verify.
/swe:playbook-review check this PR at its head commit
/swe:playbook-cifix fix red check on open PR #42
/swe:playbook-solo run the entire task in this chat without delegation
```

| Playbook | Purpose |
|---|---|
| `/swe:playbook-deliver` | End-to-end delivery: goal to merged PR and verified code |
| `/swe:playbook-feature` | Feature development from specification to verified implementation |
| `/swe:playbook-bugfix` | Defect reproduction with failing test first, minimal fix, verification |
| `/swe:playbook-review` | Read-only adversarial review of a PR or diff with command proof |
| `/swe:playbook-cifix` | Investigation and fix for failing CI check on an open PR |
| `/swe:playbook-docs` | Documentation authoring or synchronization with code changes |
| `/swe:playbook-rebase` | Bring PR branch up to date with main and safely resolve conflicts |
| `/swe:playbook-land` | Execute verify gate and squash merge approved PR |
| `/swe:playbook-changelog` | Audit and update CHANGELOG.md for merged PRs |
| `/swe:playbook-verify` | Drive live application verification against feature map |
| `/swe:playbook-solo` | Execute task end-to-end in active chat without delegation |
| `/swe:playbook` | Dispatcher and overview of all available engineering playbooks |

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
