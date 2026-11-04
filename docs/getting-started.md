# Getting started

Ten minutes from a fresh clone to `/swe` working in your coding agent.

## 1. Prerequisites

| Tool | Why | Check |
|---|---|---|
| `git`, `make`, `python3` (3.11+) | build and install the plugin | `make --version && python3 --version` |
| Claude Code and/or oh-my-pi (`omp`) | the coding agents | `claude --version`, `omp --version` |
| `gh` (GitHub CLI), logged in | PRs, issues, merges | `gh auth status` |
| Go, `uv`, Node 22 | only to run the template checks and tests | `go version`, `uv --version`, `node --version` |
| tmux (or Orca) | only for the multi-project fleet (step 5) | `tmux -V` |

## 2. Build and validate

```bash
cd swe-skills
make validate          # renders dist/swe/ and checks it: 31 skills checked, 0 error(s)
```

The plugin's name comes from `plugin.env` (`PLUGIN_NAME ?= swe`). Change it there, or per command
(`PLUGIN_NAME=acme make claude`). Private values (your real domain) go in a git-ignored
`plugin.local.env`: `PLUGIN_DOMAIN ?= mycompany.io`.

## 3. Install into your coding agent

```bash
make claude            # Claude Code: /swe, /swe:<skill>, subagents swe:worker and swe:adversary
make omp               # oh-my-pi:    /skill:swe, /skill:<skill>
make codex             # Codex (optional): $swe:swe
make hermes            # Hermes (optional): skills swe, swe-<skill>
```

Any of 31 harnesses works the same way (`make cursor`, `make gemini-cli`, `make opencode`, ...): see
[harnesses.md](harnesses.md). Start a new session afterwards. Per-agent details: [setup-claude.md](setup-claude.md) and
[setup-omp.md](setup-omp.md).

## 4. First task

In any git repository, in Claude Code:

```text
/swe            ← prints every skill, grouped
/swe the orders consumer double-counts fills when Kafka redelivers. repro first, then fix and verify.
```

The router restates your goal and a done-predicate, picks the language (Go/Fiber for APIs, Python
for ML, Rust for performance, Next.js or Vite + React for frontends), picks a playbook (here
`bug-fix`), opens the matching skills and principles, and finishes only when `make verify` passes.
In oh-my-pi the same request is `/skill:swe ...`.

A project needs `make verify` for "done" to mean something: run `/swe:verify-create` once in it
([usage.md](usage.md#give-a-project-proof)).

## 5. Optional: run several projects with the fleet

Only once step 4 works well on one repo by hand. A project is a directory holding one or more repo clones; its
orchestrator is any CLI agent (Claude Code, Codex or oh-my-pi). Hermes is optional (`board.enabled`).

```bash
ln -sf "$PWD"/fleet/bin/fleet ~/.local/bin/fleet
bash fleet/tests/selftest.sh               # proves the fleet against fake CLIs, a scratch repo and a fake Orca
fleet models check                         # fix what it lists
fleet project add orders --dir ~/work/orders --repo api=acme/orders-api --repo web=acme/orders-web \
  --description "Orders API and dashboard"      # creates the directory and clones both repos
fleet doctor orders                        # git credentials, CLIs, tmux or Orca, the clones
fleet orchestrate orders                   # start the orchestrator (default claude) in ~/work/orders
```

Which models and which agents: [recommended-setup.md](recommended-setup.md). The design:
[architecture.md](architecture.md).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `/swe` is unknown | start a new session; `claude plugin list` should show `swe@swe-skills` |
| `make validate` fails on a placeholder or name | read the first ERROR line; the validator names the file and line |
| `fleet models check` lists `omp has no model ...` | `omp login <provider>`, then `omp models ls` and put the exact id in `fleet/models.yaml` |
| `gh auth status` fails inside a delegated session | `gh auth login` for the user that runs the orchestrator |
| old `kim` or other plugin still listed | `PLUGIN_NAME=<old> make claude codex omp hermes REMOVE=1` |
