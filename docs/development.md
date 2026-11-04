# Development

For people changing this repo. Agents working here: read `../AGENTS.md` first.

## Name and build settings

The plugin's name comes from the build; the default is **`swe`**.

```bash
make claude                      # plugin "swe"   ->  /swe, /swe:go-code, ...
PLUGIN_NAME=acme make claude     # plugin "acme"  ->  /acme, /acme:go-code, ...
```

Build settings live in `plugin.env`. Put private values (your real domain, owner) in a git-ignored `plugin.local.env`, for example
`PLUGIN_DOMAIN ?= mycompany.io`. An environment variable always wins.

## Enforced, not just written

| Rule | Enforcer |
|---|---|
| Go data structs: no pointers, no `omitempty` | `go-code/scripts/structcheck` (Go tests; run by `make verify`) |
| Python: no pydantic, no pandas | ruff `TID251` in the py-code template |
| goose migrations: `CONCURRENTLY`, defaults, destructive markers | `db-migrations/scripts/check_migrations.py` |
| API contract: `/v1`, `/docs`, `/healthz`, port 3000 | `api-contract/scripts/audit_api.py`, `probe_api.py` |
| money-path: replay, duplicates, redelivery | `replay-test/scripts/replay.py` |
| TypeScript: strict, no `any`, no `console` | the `ts-code` templates' `tsconfig.json` and ESLint config |
| architecture: layers and imports | Go `archcheck`, Python `lint-imports` (both in `make verify`) |
| a good submit: branch, title, body, issue, size, scope | `github/scripts/pr_lint.py` |
| repo: squash only, protected `main`, labels | `project/scripts/setup_repo.sh` |
| "done" means proven | `verify-create/assets/verify.mk` + the `verify` CI job in `deployment-setup` |

## Make targets

| Target | What it does |
|---|---|
| `make build` | render `dist/<name>/` from `src/` |
| `make validate` | build, then validate (names, links, groups, portability, placeholders) |
| `make install` | build, validate, install into every harness detected on this machine |
| `make <harness>` | install into that harness only: `make claude`, `make codex omp hermes ...` |
| `make harness` (`make list`) | list every supported harness (55), detected ones marked |
| `make skills` | list the skills |
| `make <harness> REMOVE=1` | uninstall (only what this tool installed) |
| `make cli` | link the `<name>-cli` command into `~/.local/bin` |
| `make test` | build, enforcement, frontend and cli tests |
| `make docs` | regenerate `docs/skills.md` from the skills |
| `make package` | `dist/<name>-<version>.zip` |
| `make publish` | release `dist/<name>/` into a publish repo, commit and tag (`PUSH=1` pushes) |

## Layout

```
plugin.env           build settings (name, owner, version, domain, description)
src/skills/          the skills; src/skills/router/ becomes /<name>
src/agents/          Claude Code subagents (worker, adversary); models from cli/templates/config.yaml
src/manifests/       plugin manifests with placeholders
scripts/             build.py, install.py, validate_skills.py, gen_docs.py, publish.sh
cli/                 the `<name>-cli` command, workflows/, config.yaml, templates/ (config.yaml, PROJECT.md, learn skill), briefs, tests
docs/                architecture.md (the design), agents-and-skills.md (the recommended setup)
tests/               build_test.sh, enforcement_test.sh, fixtures
CHANGELOG.md         one entry per version (make publish requires it)
dist/                build output (git-ignored); never edit it
```
