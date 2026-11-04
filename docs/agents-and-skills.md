# Agents and skills: the recommended setup

Which agent has which skills and tools, and why. `swe-cli bootstrap` and `swe-cli project add` apply
the project directories from the project's `config.yaml`; this page is the reference behind it.

## Roles and their skills

Every role is one agent session started by a workflow node (or by the manager). The role names its skills in
the `roles:` block of `config.yaml`; the brief tells the agent to use only those. Skills name agents, never models; the cli, model and reasoning
come from the project's `config.yaml` (the one place agents are defined).

| Role | Agent | Skills it enables | Edits code? | Merges? |
|---|---|---|---|---|
| Manager (one per project) | the `manager` agent, any CLI; started in the project directory with its `AGENTS.md` | `manager`, `project`, `github`, `ketchup` | no | through the gate (`flow merge`), with approval where required |
| Intake (chat to goals) | any harness, a light agent | `intake`, `github` | no | no |
| Planner | the `planner` agent, read-only | `planner`, `architect`, `how`, `project`, `github` | no | no |
| Developer | the `developer` agent (a card may name `developer-senior`), own worktree | `developer`, `swe`, `tdd`, `deslop`, `github` | yes, its files | no |
| Documenter | the `documenter` agent (Haiku), no reasoning flag | `documenter`, `deslop`, `github` | docs only | no |
| Reviewer | the `reviewer-junior` agent (a card may name `reviewer-senior`), the author's worktree | `reviewer`, `interrogate`, `why`, `integrator`, `github` | conflict files of its card | no |
| CI fixer | the `ci-fixer` agent | `ci-fixer`, `tdd`, `github`, `blast-radius` | its card's files | no |
| Integrator | project CLI, `mid` | `integrator`, `github`, `why`, `tdd` | conflict files of its card | no |
| Verifier (nightly) | project CLI, `low`, read-only | `verifier`, `verify-maintain`, `correct`, `github` | no (files issues) | no |
| Staff (later) | resident `platform` project | not yet | its own repo only | no |
| Merge gate | code (`swe-cli merge`) | n/a | no | yes, the only path |

Not built yet: a supervisor daemon (the runner has timeouts and stuck detection only), a chat adapter for intake
(the `SWE_NOTIFY` out-hook exists), and fork support in code (`github/references/fork.md` describes it).

## Managers

Every project has one manager: any CLI agent (Claude Code, Codex, oh-my-pi, opencode) started in the project directory
by `swe-cli orchestrate <project>`, running the `manager`, `project` and `github` skills. It creates issues, starts
the coding sessions and merges through the gate; it never edits code. It answers questions itself with the read-only skills. The
default is `manager:` in `config.yaml`; a project overrides it with `manager:` in `project.yaml`.

## Coding CLIs (started by the manager in worktrees)

| CLI | Plugin | Skills used most | Subagents |
|---|---|---|---|
| Claude Code | `swe@swe-skills` (`make claude`) | `/swe` (the router), the language skills, `tdd`, `architect`, `interrogate`, `deslop`, `github` | `swe:worker`, `swe:adversary` |
| oh-my-pi | `swe@swe-skills` (`make omp`) | `/skill:swe` and the same skills | omp's own roles (optional `omp_roles` in `config.yaml`) |
| Codex | `swe@swe-skills` (`make codex`) | `$swe:swe` and the same skills | — |

Inside a card, the CLI follows the router: language by the job (Go/Fiber APIs, Python ML, Rust
performance, Next.js or Vite frontends), a playbook, the principles, `make verify`, and the `github`
skill for every git and GitHub action.

## GitHub access

| Who | Branch and push | Open and update PRs | Issues and labels | Comment and review | Merge |
|---|---|---|---|---|---|
| root | — | — | read | read | never |
| `pm-<project>` | — | — | create, label, close as "not planned" | yes | `swe-cli merge`: with `--approved` when the human says so, or for a risk class autopilot allows |
| coding CLIs | yes (own branch only, never `main`) | yes | comment | verdicts as comment reviews | no: the manager runs the gate |
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
