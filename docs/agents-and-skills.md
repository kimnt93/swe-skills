# Agents and skills: the recommended setup

Which agent has which skills and tools, and why. `fleet bootstrap` and `fleet project add` apply
the Hermes part from `fleet/models.yaml`; this page is the reference behind it.

## Hermes profiles

| Profile | Role | Skills to enable | Tools | Model (default) | Can |
|---|---|---|---|---|---|
| `default` (root) | general purpose: manages projects and profiles, routes requests, reports across projects | `fleet-admin`, `github` | kanban, terminal, memory (no file, code execution, browser, delegation) | Gemini 3.8 Flash | run `fleet` and `hermes` commands, read GitHub, create cards on any board |
| `pm-<project>` | the project's manager: orchestrator only | `fleet-manager`, `project`, `github` | kanban, terminal, memory (no file, code execution, web, browser, delegation) | Sonnet 5.5 | create and label issues, create and supervise cards, comment, report, merge with `--approved` when the human says so |
| `claude` | lane: implements and reviews (reviews the omp lane's work) | `fleet-worker`, `github` | default minus web and browser | Gemini 3.8 Flash (drives Claude Code) | run `fleet lane`, push branches, open PRs, post verdicts, run the merge gate |
| `omp` | lane: implements and reviews (reviews the claude lane's work) | `fleet-worker`, `github` | default minus web and browser | Gemini 3.8 Flash (drives oh-my-pi) | the same as `claude` |

The root profile also has the slash command `/sync` (`quick_commands.sync`): `fleet sync` with no model call, which shares the
root's API keys with every profile and applies models, context limits and skills ([context-and-sync.md](context-and-sync.md)).

Every profile's `skills.external_dirs` points at the built plugin: `dist/<plugin>/fleet/skills` (the
fleet skills) and `dist/<plugin>/skills` (the plugin's skills, such as `github` and `project`).
A card force-loads the skills it needs: `--skill fleet-worker --skill github`.

## Coding CLIs (inside a lane)

| CLI | Plugin | Skills used most | Subagents |
|---|---|---|---|
| Claude Code | `swe@swe-skills` (`make claude`) | `/swe` (the router), the language skills, `tdd`, `architect`, `interrogate`, `deslop`, `github` | `swe:worker`, `swe:adversary` |
| oh-my-pi | `swe@swe-skills` (`make omp`) | `/skill:swe` and the same skills | omp's own roles (`omp_roles` in `models.yaml`) |
| Codex (by hand, not a lane) | `swe@swe-skills` (`make codex`) | `$swe:swe` | — |

Inside a card, the CLI follows the router: language by the job (Go/Fiber APIs, Python ML, Rust
performance, Next.js or Vite frontends), a playbook, the principles, `make verify`, and the `github`
skill for every git and GitHub action.

## GitHub access

| Who | Branch and push | Open and update PRs | Issues and labels | Comment and review | Merge |
|---|---|---|---|---|---|
| root | — | — | read | read | never |
| `pm-<project>` | — | — | create, label, close as "not planned" | yes | only `fleet merge --approved`, when the human says so |
| lanes | yes (own branch only, never `main`) | yes | comment | verdicts as comment reviews | the gate, when autopilot allows the risk |
| human | — | — | anything | approve | anything (GitHub UI, or tell the manager) |

Setup once per repo, by the manager or by hand: `src/skills/project/scripts/setup_repo.sh
<owner>/<repo>` (squash only, protected `main` with the required `verify` check, labels), then copy the
templates from `src/skills/project/assets/github/` into `.github/`.

All agents run `gh` as the human's account today (`gh auth status`). Because GitHub refuses an
approval from the PR's own author, required approvals are 0 and verdicts are comment reviews; the
gate (`fleet merge`) enforces the review. With a bot account, rerun `setup_repo.sh --approvals 1`
and let lanes use `gh pr review --approve`.

## Submitting well

Every agent that writes code follows the `github` skill's submit rules, and `pr_lint.py` plus
`make verify` check them: one feature function per PR, at most about 400 changed lines, the simplest
code that works, only the files the card allows, the project's architecture respected (Go
`archcheck`, Python `lint-imports`), tests with the change, `make verify` green, a linked issue.
