# 03 — enforcement

status: done

## Goal

Rules that lived only in skill prose fail a check, in the templates every new service starts from.

## What exists

| Rule | Enforcer | Proof |
|---|---|---|
| Go data structs: no pointers, no `omitempty` | `src/skills/go-code/scripts/structcheck` (stdlib Go, `//structcheck:allow <reason>` escape) | Go tests; clean template passes; `tests/fixtures/bad-go` fails with both findings |
| Python: no pydantic, no pandas | ruff `TID251` banned-api in the py-code template `pyproject.toml`, messages naming msgspec and polars | clean template passes; `tests/fixtures/bad-py` fails |
| migrations, API contract | `check_migrations.py`, `audit_api.py`, `probe_api.py` | existing self-test and scripts |
| proof before done | `verify.mk` runs all of the above + structcheck + e2e + a live probe; the `deployment-setup` CI template has a `verify` job to make required | `tests/enforcement_test.sh` renders it |
| frontend templates: strict TS, lint, tests, build, e2e, images | `ts-code` templates; `deployment-setup` Dockerfiles | `tests/frontend_test.sh --e2e --docker` |
| plugin hygiene | the validator; "no org name" in `tests/build_test.sh` | `make validate`, `make test` |

## Verify

```bash
bash tests/enforcement_test.sh
bash tests/frontend_test.sh --e2e --docker
```

## Log

- 2026-11-02: frontend templates and images tested (install, typecheck, lint, tests, build, Playwright, /healthz in Docker).

- 2026-11-02: structcheck, ruff banned-api, CI verify job, fixtures and the enforcement test.
