# Getting started

Ten minutes from a fresh clone to `/swe` working in your coding agent.

## 1. Prerequisites

| Tool | Why | Check |
|---|---|---|
| `git`, `make`, `python3` (3.11+) | build and install the plugin | `make --version && python3 --version` |
| Claude Code and/or oh-my-pi (`omp`) | the coding agents | `claude --version`, `omp --version` |
| `gh` (GitHub CLI), logged in | PRs, issues, merges | `gh auth status` |
| Go, `uv`, Node 22 | only to run the template checks and tests | `go version`, `uv --version`, `node --version` |
| Orca (optional) | the playbooks' worktrees and messages between agents | `orca status` |

## 2. Build and validate

```bash
cd swe-skills
make validate          # renders dist/swe/ and checks it: 52 skills checked, 0 error(s)
```

The plugin's name comes from `plugin.env` (`PLUGIN_NAME ?= swe`). Change it there, or per command
(`PLUGIN_NAME=acme make claude`). Private values (your real domain) go in a git-ignored
`plugin.local.env`: `PLUGIN_DOMAIN ?= mycompany.io`.

## 3. Install into your coding agent

```bash
make claude            # Claude Code: /swe, /swe:<skill>, subagents swe:worker and swe:adversary
make omp               # oh-my-pi:    /skill:swe, /skill:<skill>
make codex             # Codex (optional): $swe:swe
```

`make install` installs into every harness detected on the machine; `make harness` (or `make list`) lists the 55
supported ones with the detected ones marked; `make <harness>` installs into just that one.

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

## 5. Run a playbook

Once step 4 works on one repository, let a playbook carry work through GitHub. The
[merge rules](playbooks.md#merge-rules) check uses your `gh` login as it is.

| Say | What happens |
|---|---|
| `/swe:playbook-review review PR 54` | one `PASS` or `FAIL` comment; nothing changes. A safe first try |
| `/swe:playbook-plan <problem>` | a planning issue and a plan comment; stops when the plan is accepted |
| `/swe:playbook-quick <problem>` | issues, pull requests, the CTO/CEO's check and merge |
| `/swe:playbook-complete <problem or plan>` | issues, pull requests, a separate reviewer who also fixes, then the merge |
| `/swe:playbook-ship ship PR 54` | review and fix, then merge and close the issue |

Work is built and merged only for an approved issue. To approve one, comment `Accepted by owner.` on it: only this
comment approves. An issue your account created and a board status `Todo` or `In Progress` are off while agents share
your account. More:
[playbooks.md](playbooks.md). To make `swe-cli` available, run `make cli`; its commands are in
[cli/README.md](../cli/README.md).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `/swe` is unknown | start a new session; `claude plugin list` should show `swe@swe-skills` |
| `make validate` fails on a placeholder or name | read the first ERROR line; the validator names the file and line |
| the merge check says the board status cannot be read | run it again; if it still fails, check `gh auth status` and GitHub's status |
| the merge check says the board was not read | the `gh` login lacks the scope for project boards; the check went on without them ([what is not checked](../src/skills/github/references/pull-requests.md#merge-rules)) |
| the merge check says an issue is not approved | comment `Accepted by owner.` on it yourself; your authorship and a board status of `Todo` do not approve while agents share your account |
| `gh auth status` fails inside a delegated session | `gh auth login` for the user that runs the session |
| old `kim` or other plugin still listed | `PLUGIN_NAME=<old> make claude codex omp REMOVE=1` |
