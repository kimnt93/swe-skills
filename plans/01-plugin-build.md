# 01 — plugin-build

status: done

## Goal

`make` renders a complete, installable plugin under any name and domain, and proves it.

## What exists

- `plugin.env` (+ git-ignored `plugin.local.env`, + environment variables) holds the build settings.
- `scripts/build.py`: copies `src/skills`, renames the router, fills the placeholders in every text
  file, writes the grouped skill index, sets each subagent's model from `fleet/models.yaml`, renders
  the manifests (dropping empty fields), copies `src/agents`, `fleet/skills`, the installer, the
  validator, `UPSTREAM`, `LICENSES`, `CHANGELOG.md`, and writes `LICENSE`, `README.md`,
  `build.json`. It refuses a bad name, a name that collides with a skill, and any placeholder left.
- `scripts/install.py`: plugin install for Claude Code, Codex and omp; copy install elsewhere
  (router unprefixed, other skills `<name>-<skill>`); uninstall touches only what it installed.
- `scripts/validate_skills.py`: names, links in every file, groups, portability, upstream metadata,
  dangling skill and principle references, placeholders.

## Verify

```bash
make validate                                        # 25 skills checked, 0 error(s)
PLUGIN_NAME=acme PLUGIN_DOMAIN=acme.test make validate
bash tests/build_test.sh --claude                    # incl. /qa and the qa:worker / qa:adversary agents in Claude Code
make package                                         # dist/<name>-<version>.zip
```

## Log

- 2026-11-02: first build (as "developer", then renamed); default name `kim`; domain and owner made build settings.
