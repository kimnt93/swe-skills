# Changelog

Versions follow semver: a new skill or a rule a skill newly enforces is a minor version; wording
and fixes are a patch. `make publish` refuses a version without an entry here.

## 1.0.0

First release.

- 31 skills in six groups (start, process, language, data, platform, observability) for the stack:
  Go/Fiber APIs, Python ML, Rust performance, Next.js and Vite + React + TypeScript frontends.
- Builds as the plugin `swe` (name, owner and version from `plugin.env`) for Claude Code, Codex and
  oh-my-pi, and as plain skills for 28 more harnesses.
- Fleet on Hermes Kanban: one manager profile per project, shared `claude` and `omp` lanes, a merge
  gate, model and context limits in `fleet/models.yaml`, and a `/sync` command.
- Tested scripts and templates ship with the skills; `make validate` and `make test` check them.
