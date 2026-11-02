# Working in swe-skills (for AI agents)

Read this file fully, then `docs/README.md` (and `docs/runbooks.md` for operations), before you change anything.

## What this repo is

The source of a software-engineering plugin. `scripts/build.py` renders it into
`dist/<PLUGIN_NAME>/` (default name `swe`): a complete plugin for Claude Code, Codex and omp, and
plain skills for every other harness. `fleet/` runs the plugin's agents on Hermes Kanban with two
coding lanes (`claude`, `omp`); every agent and model is set in `fleet/models.yaml`.

## Rules

1. **Edit `src/`, `fleet/`, `scripts/`, `tests/`, `docs/`. Never edit `dist/`.** `docs/skills.md` and `docs/harnesses.md` are generated (`make docs`). It is rebuilt from
   scratch on every `make build`.
2. **Never hard-code the plugin's name or the org's values.** The build fills these placeholders:
   `@PLUGIN@` (plugin and router name), `@DOMAIN@` (hosts and URLs: `<service>.<env>.@DOMAIN@`),
   `@OWNER@`, `@HOMEPAGE@`. Private values (a real domain) go in the git-ignored
   `plugin.local.env`, never in a tracked file. `tests/build_test.sh` fails on an org name.
3. **Skills stay flat:** `src/skills/<name>/SKILL.md`, `name` equal to the directory, matching
   `^[a-z0-9]+(-[a-z0-9]+)*$`. A short `SKILL.md` router, one topic per `references/*.md` (each
   linked from `SKILL.md`), tested files in `assets/` and `scripts/`. The router lives in
   `src/skills/router/` and is renamed to the plugin's name at build.
4. **Every skill has `metadata.group`:** `start`, `process`, `language`, `data`, `platform` or
   `observability`. The router index and the plugin README group by it.
5. **Harness-neutral text.** Say "start a subagent at tier T", never a tool name or a model slug.
   The how-to lives in `src/skills/router/references/harness.md`. Model ids live only in
   `fleet/models.yaml`.
6. **Forking from pstack:** copy into this repo's format, add `metadata.upstream`, add a row to
   `UPSTREAM`, keep the MIT notice. Adapt until `make validate` is green: it flags Cursor-only terms,
   `**x** skill` references to skills we don't have, `**x** principle` references with no file,
   broken links, missing groups and leftover placeholders.
7. **Anything a skill ships that runs is tested:** a `--self-test` (run by
   `tests/enforcement_test.sh`), a Go test, or a case in `tests/`.
8. **A repeated mistake becomes a check** in the validator or a test, not a sentence in this file.
9. **A placeholder is replaced everywhere**, prose included. To talk *about* a placeholder in a
   skill, describe it ("the plugin-name placeholder from AGENTS.md"); don't write it.

## Commands

```bash
make validate                               # build + validate (after every change)
make test                                   # build, enforcement, frontend and fleet tests
bash tests/frontend_test.sh --e2e --docker # also Playwright and the frontend images
bash tests/build_test.sh --claude           # also load the built plugin in Claude Code (a few Haiku tokens)
bash fleet/tests/selftest.sh --hermes       # also bootstrap a scratch Hermes home
PLUGIN_NAME=acme PLUGIN_DOMAIN=acme.test make validate   # any name and domain must build too
```

Done means `make validate` and `make test` pass, and you ran the checks of the runbook you touched.

## Commits

Conventional Commits, small and ordered: `feat(skills): ...`, `fix(build): ...`, `docs(runbooks): ...`.
Don't commit `dist/` or `plugin.local.env`. Don't push unless the plan or the human says so.
