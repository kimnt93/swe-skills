# Changelog

Versions follow semver: a new skill or a rule a skill newly enforces is a minor version; wording
and fixes are a patch. `make publish` refuses a version without an entry here.

## 1.0.0

First release.

- 40 skills in six groups (start, process, language, data, platform, observability; nine of them are the roles of workflow agents) for the stack:
  Go/Fiber APIs, Python ML, Rust performance, Next.js and Vite + React + TypeScript frontends.
- Builds as the plugin `swe` (name, owner and version from `plugin.env`) for Claude Code, Codex and
  oh-my-pi, and as plain skills for 28 more harnesses.
- `swe-cli` (`<plugin>-cli`, linked by `make cli`): `swe-cli init` turns a directory into a project: `AGENTS.md` for the
  orchestrator, `workflows/*.yaml`, `roles.yaml`, `models.yaml` and `project.yaml` (the repo URLs and their folders), then
  asks for git URLs until you are done and clones them. `swe-cli project add <git url>` adds one later; the manager can too.
- Workflows: YAML DAGs run by a small Python runner (`swe-cli flow`). Each node is one agent with only the skills of its
  role, on the harness, model and effort that fit it; nodes run in parallel and write reports to a tmp directory; the
  manager merges the ready PRs through the gate and `flow clean` removes sessions, worktrees, branches and tmp files. A
  reviewer agent brings a behind branch up to date and resolves conflicts. Shipped: feature, bugfix, docs, card, docs-card,
  ci-fix, conflict, verify.
- Agents start coding CLIs (Claude Code, Codex, oh-my-pi) in a tmux session or an Orca terminal and a git worktree per
  card, refuse cards whose files overlap (also across projects that clone the same repo), keep branch names unique, and
  merge only through the gate (`swe-cli merge`, which also refuses a branch behind `main`). `swe-cli doctor` checks
  credentials first. Models, context limits, orchestrator and launcher live in `models.yaml`; Hermes is optional.
- Tested scripts and templates ship with the skills; `make validate` and `make test` check them.
