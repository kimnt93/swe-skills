# Working in swe-skills (for AI agents)

Read this file fully, then `docs/README.md` (and `docs/runbooks.md` for operations), before you change anything.

## What this repo is

The source of a software-engineering plugin. `scripts/build.py` renders it into
`dist/<PLUGIN_NAME>/` (default name `swe`): a complete plugin for Claude Code, Codex and omp, and
plain skills for every other harness. The stack runs in **Orca**: Orca bots hold the roles and orchestrate, and Orca
runs their agents in the harnesses, started with the `delegate` skill. Workflows are structured **playbooks**
(`playbook-*` skills). Which harness, model and reasoning effort an agent runs on comes only from the team's **agent
table** (`bot-orchestration`), kept outside this repository; `config.json` (`$SWE_CONFIG` or
`~/.config/@PLUGIN@/config.json`) may name where it is. `cli/` is the `<name>-cli` command (`swe-cli`): `update`,
`agents`, `delegate`, `playbooks`, `config`, `doctor`.

## Rules

1. **Edit `src/`, `cli/`, `scripts/`, `tests/`, `docs/`. Never edit `dist/`.** `docs/skills.md` and `docs/harnesses.md` are generated (`make docs`). It is rebuilt from
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
5. **Harness-neutral text.** Say "start a subagent on a row of the agent table", never a harness's tool name or a
   model id. The how-to lives in `src/skills/router/references/harness.md`. No tracked file names a model: harness,
   model and effort live only in each team's own agent table.
6. **Skills describe this stack only:** no repository, project or tool-specific names (the validator
   flags them), a `metadata.summary` of one line (it becomes the skill's row in the docs tables), and
   no `**x** skill` or `**x** principle` reference without a file, broken link, missing group or
   leftover placeholder. `make validate` checks all of it.
7. **Anything a skill ships that runs is tested:** a `--self-test` (run by
   `tests/enforcement_test.sh`), a Go test, or a case in `tests/`.
8. **A repeated mistake becomes a check** in the validator or a test, not a sentence in this file.
9. **A placeholder is replaced everywhere**, prose included. To talk *about* a placeholder in a
   skill, describe it ("the plugin-name placeholder from AGENTS.md"); don't write it.

## Commands

```bash
make validate                               # build + validate (after every change)
make test                                   # build, enforcement, frontend and cli tests (selftest, flowtest, inittest)
bash tests/frontend_test.sh --e2e --docker # also Playwright and the frontend images
bash tests/build_test.sh --claude           # also load the built plugin in Claude Code (uses a few tokens)
PLUGIN_NAME=acme PLUGIN_DOMAIN=acme.test make validate   # any name and domain must build too
```

Done means `make validate` and `make test` pass, and you ran the checks of the runbook you touched.

## Commits

Conventional Commits, small and ordered: `feat(skills): ...`, `fix(build): ...`, `docs(runbooks): ...`.
Don't commit `dist/` or `plugin.local.env`. Don't push unless the plan or the human says so.
