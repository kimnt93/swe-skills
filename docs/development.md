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
| one place sets harness, model and effort | `agent_table.py` (no default), the "one agent table" checks in `tests/enforcement_test.sh` |
| Orca is the only way agents start; no model id in a tracked file | `tests/enforcement_test.sh` |
| a good submit: branch, title, body, issue, size, scope | `github/scripts/pr_lint.py` |
| repo: rebase only, protected `main`, labels | `project/scripts/setup_repo.sh` |
| "done" means proven | `verify-create/assets/verify.mk` + the `verify` CI job in `deployment-setup` |
| security and outbound data on every reviewed PR: the verdict's `## Security` section, no unasked outbound path | `work-package/scripts/package_lint.py`, `github/scripts/pr_loop.py`, `issue_gate.py asked`; their self-tests and `tests/enforcement_test.sh` |
| the security scan: sends nothing, prints no secret, never reads a broken diff as clean | `security-review/scripts/security_scan.py --self-test`; the fixture diffs in `tests/fixtures/security-diffs` |
| a test run: allowed targets, production approvals, secrets and evidence outside repositories | `web-testing/scripts/testkit.py`, `web_test.py`, `api-cli-testing/scripts/io_test.py`; their self-tests and `tests/testing_skills_test.sh` |

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
| `make test` | build, enforcement, harness, frontend, testing-skill and cli tests |
| `make docs` | regenerate `docs/skills.md`, `docs/harnesses.md` and the index in `docs/skills/README.md` |
| `make package` | `dist/<name>-<version>.zip` |
| `make publish` | release `dist/<name>/` into a publish repo, commit and tag (`PUSH=1` pushes) |

`make test` runs `tests/testing_skills_test.sh` without a browser: the API and command-line runner against the local
fixture in `tests/fixtures/web-app/`. Run the browser half after changing a testing skill. It needs `uv`, `ffmpeg` and
once `uv run --with playwright==1.65.0 playwright install chromium`; `--keep <empty directory>` keeps the evidence:

```bash
bash tests/testing_skills_test.sh --browser --keep ~/test-evidence/fixture-run
```

## Layout

```
plugin.env           build settings (name, owner, version, domain, description)
src/skills/          the skills; src/skills/router/ becomes /<name>
src/agents/          Claude Code subagents (worker, adversary); they name no model
src/manifests/       plugin manifests with placeholders
scripts/             build.py, install.py, validate_skills.py, gen_docs.py, publish.sh
cli/                 the `<name>-cli` command (bin/main) and its tests
docs/                this documentation; skills.md and harnesses.md are generated
tests/               build, enforcement, harness and frontend tests, fixtures
config.example.json  the shipped config.json: it only names where the team's agent table is
CHANGELOG.md         one entry per version (make publish requires it)
dist/                build output (git-ignored); never edit it
```
