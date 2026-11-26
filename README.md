# swe-skills

A software-engineering plugin for coding agents. One entry command (`/swe`) picks the language for the job, routes the task to
tested skills and engineering principles, and does not finish until the project's `make verify` passes. Five **playbooks**
(`/swe:playbook-<name>`) take work from a problem or a pull request to its end, and `/swe:delegate` hands tasks to other
coding agents through **Orca**, **T3 Code** or a direct CLI.

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

Exactly five. Pick by what you have and who should judge the code.

| You have | Playbook | What happens | Ends |
|---|---|---|---|
| a problem whose design is open | [`plan`](src/skills/playbook-plan/SKILL.md) ([example](src/skills/playbook-plan/references/example.md)) | CTO/CEO card → architect comments the plan → back to the CTO/CEO | at the accepted plan; nothing built |
| small or medium work | [`quick`](src/skills/playbook-quick/SKILL.md) ([example](src/skills/playbook-quick/references/example.md)) | CTO/CEO issues → one worktree and PR each → the CTO/CEO checks, at most 3 feedback rounds | merged or stopped |
| features, hard work, an accepted plan | [`complete`](src/skills/playbook-complete/SKILL.md) ([example](src/skills/playbook-complete/references/example.md)) | CTO/CEO issues → a PR each → a **reviewer** reviews and fixes → the CTO/CEO trusts the PASS | merged or stopped |
| a PR you want judged | [`review`](src/skills/playbook-review/SKILL.md) | read it, run it when safe, post one `PASS` or `FAIL` comment | at the comment; nothing changed |
| a PR you want on `main` | [`ship`](src/skills/playbook-ship/SKILL.md) ([example](src/skills/playbook-ship/references/example.md)) | one reviewer reviews, fixes and re-reviews, at most 3 rounds, then merges | merged and issue closed, or stopped |

```text
/swe:playbook-plan users cannot export the orders they filtered; plan it
/swe:playbook-quick users misread order times; fix it
/swe:playbook-complete build the accepted export plan
/swe:playbook-review review PR 54
/swe:playbook-ship ship PR 54
```

In `complete` and `ship`, nobody else checks the reviewer's own fixes before `main`. The final `PASS` names those
commits, and a `risk:money-path` pull request is never auto-merged ([fix loop](src/skills/reviewer/references/fix-loop.md)).

### Bots and agents

A **bot** is a standing member; an **agent** is a coding CLI that a bot starts for one job. The bot orchestrates:

```text
CEO bot ─ issue ─► developer bot ─ brief ─► agent (one issue, own worktree)
   ▲                  │    ▲                  │
   └──── status ──────┘    └──── report ──────┘        agents never message each other
```

Bots delegate with a handoff and report back with a status. The developer bot picks the agent by difficulty, checks its
work and opens the pull request. Rules, message templates and a linter:
[bot-orchestration](src/skills/bot-orchestration/SKILL.md).

### Merge rules: only approved work

Nothing is built or merged unless the pull request links an issue of the same repository and **every linked issue is
approved**. As shipped, only the repository owner's comment on the issue approves it
([template](src/skills/github/assets/owner-acceptance.template.md)). An issue the owner's account created and a project
board status of `Todo` or `In Progress` approve nothing: they are off while agents share the owner's account. The
`approvals` list in [merge-rules.json](src/skills/github/assets/merge-rules.json) switches them on again
(`owner_comment`, `owner_author`, `board_status`); a missing, empty or unknown value refuses everything.

```text
Accepted by owner.

Notes: none
```

An issue that is closed (done, not planned or duplicate), labelled `duplicate` or `wontfix`, or marked `Done`,
`Not planned`, `Duplicate` or `Canceled` on a board is refused whatever else says yes. Agents often share the owner's
account, so text signed by an agent never counts as the owner's. The check uses your `gh` login as it is. If GitHub
answers that the login lacks the scope for project boards, it goes on without the board and says so: a board status then
does not refuse ([what is not checked](src/skills/github/references/pull-requests.md#merge-rules)). Any
other failure to read the board refuses.

```bash
python3 src/skills/github/scripts/issue_gate.py issue <number> --repo <owner>/<repo>   # may it be built?
python3 src/skills/github/scripts/issue_gate.py pr <number> --repo <owner>/<repo>      # may it be merged?
```

These checks are run by the agents; GitHub does not enforce them. Full rules:
[merge rules](src/skills/github/references/pull-requests.md#merge-rules); the names are in
[merge-rules.json](src/skills/github/assets/merge-rules.json).

### One style for issues, comments, commits and pull requests

- Issues are written with [`write-issue`](src/skills/write-issue/SKILL.md), comments with
  [`write-comment`](src/skills/write-comment/SKILL.md), pull requests from one template.
- Every commit is authored by the agent's name, and every issue, comment and PR body ends with `Created: <agent name>`
  ([identity](src/skills/github/references/identity.md)). Merges are by rebase, so the name stays on `main`.
- The linters read the Markdown templates: edit a file to change the style
  ([the list and how](src/skills/write-issue/references/templates.md)).

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
| [docs/playbooks.md](docs/playbooks.md) | the five playbooks, their gates and rules |
| [docs/skills/](docs/skills/README.md) | each skill in detail |
| [docs/harnesses.md](docs/harnesses.md) | every supported harness and how it installs |
| [docs/development.md](docs/development.md) | make targets, build settings, layout, enforced rules |
| [cli/README.md](cli/README.md) | every `swe-cli` command |
