# Agents and skills: the recommended setup

Which agent has which skills and tools, and why. `fleet bootstrap` and `fleet project add` apply
the project directories (and, with Hermes on, the profiles) from `fleet/models.yaml`; this page is the reference behind it.

## Orchestrators

Every project has one orchestrator: any CLI agent (Claude Code, Codex, oh-my-pi) started in the project directory
by `fleet orchestrate <project>`, running the `fleet-manager`, `project` and `github` skills. It creates issues, starts
the coding sessions and merges through the gate; it never edits code. The default is `orchestrator:` in
`fleet/models.yaml`; a project overrides it. Hermes is an optional alternative (below).

## Hermes profiles (optional: `board.enabled: true`)

| Profile | Role | Skills to enable | Tools | Model (default) | Can |
|---|---|---|---|---|---|
| `default` (root) | general purpose: manages projects and profiles, routes requests, reports across projects | `fleet-admin`, `github` | kanban, terminal, memory (no file, code execution, browser, delegation) | Gemini 3.8 Flash | run `fleet` and `hermes` commands, read GitHub, create cards on any board |
| `pm-<project>` | the project's manager: a router, orchestrator only | `fleet-manager`, `project`, `github` | kanban, terminal, memory (no file, code execution, web, browser, delegation) | Gemini 3.8 Flash (not Claude: it must survive Claude's quota) | create and label issues, run `fleet delegate` (start, status, send, review, cleanup), comment, report, merge with `--approved` when the human says so |

The root profile also has the slash command `/sync` (`quick_commands.sync`): `fleet sync` with no model call, which shares the
root's API keys with every profile and applies models, context limits and skills ([context-and-sync.md](context-and-sync.md)).

Every profile's `skills.external_dirs` points at the built plugin: `dist/<plugin>/fleet/skills` (the
fleet skills) and `dist/<plugin>/skills` (the plugin's skills, such as `github` and `project`).
The coding CLIs are not Hermes profiles: they run in sessions (tmux or Orca terminals) that `fleet delegate` starts, with
the plugin installed in the CLI itself ([delegation.md](delegation.md)).

## Coding CLIs (started by the orchestrator in worktrees)

| CLI | Plugin | Skills used most | Subagents |
|---|---|---|---|
| Claude Code | `swe@swe-skills` (`make claude`) | `/swe` (the router), the language skills, `tdd`, `architect`, `interrogate`, `deslop`, `github` | `swe:worker`, `swe:adversary` |
| oh-my-pi | `swe@swe-skills` (`make omp`) | `/skill:swe` and the same skills | omp's own roles (`omp_roles` in `models.yaml`) |
| Codex | `swe@swe-skills` (`make codex`) | `$swe:swe` and the same skills | — |

Inside a card, the CLI follows the router: language by the job (Go/Fiber APIs, Python ML, Rust
performance, Next.js or Vite frontends), a playbook, the principles, `make verify`, and the `github`
skill for every git and GitHub action.

## GitHub access

| Who | Branch and push | Open and update PRs | Issues and labels | Comment and review | Merge |
|---|---|---|---|---|---|
| root | — | — | read | read | never |
| `pm-<project>` | — | — | create, label, close as "not planned" | yes | `fleet merge`: with `--approved` when the human says so, or for a risk class autopilot allows |
| coding CLIs | yes (own branch only, never `main`) | yes | comment | verdicts as comment reviews | no: the orchestrator runs the gate |
| human | — | — | anything | approve | anything (GitHub UI, or tell the manager) |

Setup once per repo, by the manager or by hand: `src/skills/project/scripts/setup_repo.sh
<owner>/<repo>` (squash only, protected `main` with the required `verify` check, labels), then copy the
templates from `src/skills/project/assets/github/` into `.github/`.

All agents run `gh` as the human's account today (`gh auth status`). Because GitHub refuses an
approval from the PR's own author, required approvals are 0 and verdicts are comment reviews; the
gate (`fleet merge`) enforces the review. With a bot account, rerun `setup_repo.sh --approvals 1`
and let the reviewing CLI use `gh pr review --approve`.

## Submitting well

Every agent that writes code follows the `github` skill's submit rules, and `pr_lint.py` plus
`make verify` check them: one feature function per PR, at most about 400 changed lines, the simplest
code that works, only the files the card allows, the project's architecture respected (Go
`archcheck`, Python `lint-imports`), tests with the change, `make verify` green, a linked issue.
