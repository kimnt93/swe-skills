# Changelog

Versions follow semver: a new skill or a rule a skill newly enforces is a minor version; wording
and fixes are a patch. `make publish` refuses a version without an entry here.

## 1.0.0

First release.

- 31 skills in six groups (start, process, language, data, platform, observability) for the stack:
  Go/Fiber APIs, Python ML, Rust performance, Next.js and Vite + React + TypeScript frontends.
- Builds as the plugin `swe` (name, owner and version from `plugin.env`) for Claude Code, Codex and
  oh-my-pi, and as plain skills for 28 more harnesses.
- Fleet: a project is a directory holding one or more repo clones. Its orchestrator is any CLI agent (Claude
  Code, Codex or oh-my-pi, started by `fleet orchestrate`); Hermes managers are optional. The orchestrator starts
  coding CLIs in a tmux session or an Orca terminal and a git worktree per card (`fleet delegate`), refuses cards
  whose files overlap, also across projects that clone the same repo, keeps branch names unique, rebases before the
  PR, and merges only through the gate (`fleet merge`, which also refuses a branch behind `main`). `fleet doctor`
  checks credentials first. Models, context limits, orchestrator and launcher live in `fleet/models.yaml`.
- Tested scripts and templates ship with the skills; `make validate` and `make test` check them.
