# Agents and skills: the recommended setup

Which agent has which skills and tools, and why. `swe-cli bootstrap` and `swe-cli project add` apply
the project directories (and, with Hermes on, the profiles) from `cli/models.yaml`; this page is the reference behind it.

## Roles and their skills

Every role is one agent session started by a workflow node (or by the manager). The role names its skills in
`cli/roles.yaml`; the brief tells the agent to use only those. Skills name tiers, never models; the model comes
from `cli/models.yaml`.

| Role | Harness / tier | Skills it enables | Edits code? | Merges? |
|---|---|---|---|---|
| Manager (orchestrator, one per project) | any CLI, `mid`; started in the project directory with its `AGENTS.md` | `manager`, `project`, `github`, `ketchup` | no | through the gate (`flow merge`), with approval where required |
| Intake (chat to goals) | cheap model or Hermes root | `intake`, `github` | no | no |
| Planner | project CLI, `mid`, high effort, read-only | `planner`, `architect`, `how`, `project`, `github` | no | no |
| Developer | project CLI, `mid` (card tier decides), own worktree | `developer`, `swe`, `tdd`, `deslop`, `github` | yes, its files | no |
| Documenter | project CLI, `low` (Haiku / gpt-6-luna), no effort flag | `documenter`, `deslop`, `github` | docs only | no |
| Reviewer | other model family, `top`, high effort, the author's worktree | `reviewer`, `interrogate`, `why`, `integrator`, `github` | conflict files of its card | no |
| CI fixer | project CLI, `mid` | `ci-fixer`, `tdd`, `github`, `blast-radius` | its card's files | no |
| Integrator | project CLI, `mid` | `integrator`, `github`, `why`, `tdd` | conflict files of its card | no |
| Verifier (nightly) | project CLI, `low`, read-only | `verifier`, `verify-maintain`, `correct`, `github` | no (files issues) | no |
| Staff (later) | resident `platform` project | not yet | its own repo only | no |
| Merge gate | code (`swe-cli merge`) | n/a | no | yes, the only path |

Not built yet: a supervisor daemon (the runner has timeouts and stuck detection only), a chat adapter for intake
outside Hermes (the `SWE_NOTIFY` out-hook exists), and fork support in code (`github/references/fork.md` describes it).

## Orchestrators

Every project has one orchestrator: any CLI agent (Claude Code, Codex, oh-my-pi) started in the project directory
by `swe-cli orchestrate <project>`, running the `manager`, `project` and `github` skills. It creates issues, starts
the coding sessions and merges through the gate; it never edits code. The default is `orchestrator:` in
`cli/models.yaml`; a project overrides it. Hermes is an optional alternative (below).

## Hermes profiles (optional: `board.enabled: true`)

| Profile | Role | Skills to enable | Tools | Model (default) | Can |
|---|---|---|---|---|---|
| `default` (root) | general purpose: manages projects and profiles, routes requests, reports across projects | `intake`, `github` | kanban, terminal, memory (no file, code execution, browser, delegation) | Gemini 3.8 Flash | run `fleet` and `hermes` commands, read GitHub, create cards on any board |
| `pm-<project>` | the project's manager: a router, orchestrator only | `manager`, `project`, `github` | kanban, terminal, memory (no file, code execution, web, browser, delegation) | Gemini 3.8 Flash (not Claude: it must survive Claude's quota) | create and label issues, run `swe-cli delegate` (start, status, send, review, cleanup), comment, report, merge with `--approved` when the human says so |

The root profile also has the slash command `/sync` (`quick_commands.sync`): `swe-cli sync` with no model call, which shares the
root's API keys with every profile and applies models, context limits and skills ([context-and-sync.md](context-and-sync.md)).

Every profile's `skills.external_dirs` points at the built plugin: `dist/<plugin>/skills` (the plugin's skills, such as `manager`, `intake`, `github` and `project`).
The coding CLIs are not Hermes profiles: they run in sessions (tmux or Orca terminals) that `swe-cli delegate` starts, with
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
| `pm-<project>` | — | — | create, label, close as "not planned" | yes | `swe-cli merge`: with `--approved` when the human says so, or for a risk class autopilot allows |
| coding CLIs | yes (own branch only, never `main`) | yes | comment | verdicts as comment reviews | no: the orchestrator runs the gate |
| human | — | — | anything | approve | anything (GitHub UI, or tell the manager) |

Setup once per repo, by the manager or by hand: `src/skills/project/scripts/setup_repo.sh
<owner>/<repo>` (squash only, protected `main` with the required `verify` check, labels), then copy the
templates from `src/skills/project/assets/github/` into `.github/`.

All agents run `gh` as the human's account today (`gh auth status`). Because GitHub refuses an
approval from the PR's own author, required approvals are 0 and verdicts are comment reviews; the
gate (`swe-cli merge`) enforces the review. With a bot account, rerun `setup_repo.sh --approvals 1`
and let the reviewing CLI use `gh pr review --approve`.

## Submitting well

Every agent that writes code follows the `github` skill's submit rules, and `pr_lint.py` plus
`make verify` check them: one feature function per PR, at most about 400 changed lines, the simplest
code that works, only the files the card allows, the project's architecture respected (Go
`archcheck`, Python `lint-imports`), tests with the change, `make verify` green, a linked issue.
