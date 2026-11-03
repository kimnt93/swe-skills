---
name: verify-create
description: "Give a project a scripted way to prove behaviour like a user would: a `make verify` lever and a project-local verify skill with a feature map, for Go/Fiber APIs, Python ML or data services, Rust services, and Next.js or Vite + React frontends. Use when a repo has no scripted proof, or before running agents on it unattended."
metadata:
  group: process
  summary: "Give a project make verify and a verify skill that drives it like a user"
---

# Verify create

A project needs one command that proves it works, and a skill that tells the next agent how to
drive it like a user. Build both, and prove them once end to end.

## 1. Answer from the repo

- **Surface:** HTTP API (Go/Fiber, Litestar), Kafka consumer, batch or ML job, Rust service or
  library, web frontend. A repo can have several; start with the primary one.
- **Run:** the infra (`docker compose -f docker-compose.infra.local.yaml up -d --wait`, from
  `deployment-setup`), then the app: `go run ./cmd/api`, `uv run python -m service`,
  `cargo run --release`, `pnpm dev` / `npm run dev`.
- **Doctor:** `GET /healthz` (the `api-contract` skill) for services; the dev server answering for frontends.
- **Drive:** HTTP against `/v1/...`; produce to and consume from the topics; read rows back; for
  ML, run the evaluation on the fixed split; for frontends, Playwright against the running app.
- **Evidence:** response bodies, rows, offsets, metrics, evaluation scores, screenshots and traces.

## 2. The lever: `make verify`

Copy [`assets/verify.mk`](assets/verify.mk) into the repo and `include verify.mk` from its Makefile.
Set `RUN`, `E2E`, `SERVICE`, `PORT`. Vendor the check scripts it calls into `tools/skills/` with the
same layout (`api-contract/scripts/`, `db-migrations/scripts/`, `go-code/scripts/structcheck/`,
`go-code/scripts/archcheck/`), so
CI runs what agents run. Per surface, `make verify` must include:

| Surface | Static | Live |
|---|---|---|
| Go/Fiber API | `golangci-lint`, `go test -race`, structcheck, archcheck (the layering), `audit_api.py`, `check_migrations.py` | e2e tests, `probe_api.py` |
| Python ML or data | `ruff check`, `lint-imports` (the layering), `pytest` | the evaluation on a fixed split, its metric against a floor |
| Rust | `cargo fmt --check`, `clippy -D warnings`, `cargo test` | the service probe or the bench smoke run |
| Frontend | `tsc --noEmit`, `eslint`, `vitest run` | `next build` or `vite build`, then `playwright test` |
| money-path | — | the `replay-test` checks (clean, duplicate, redelivery) |

CI's `verify` job (the `deployment-setup` workflow template) runs the same target; make it a
required check.

## 3. The verify skill

Write `.agents/skills/verify-<app>/SKILL.md` (frontmatter with `name: verify-<app>` and a
description naming the app and its surface) with sections: **Launch** (the exact command and how to
tell it is ready), **Doctor** (one read-only health check), **Drive** (real commands, routes and
selectors from this repo), **Evidence** (what to capture and where it survives cleanup), **Cleanup**
(stop only what you started). Seed the feature map: `features/README.md` plus one file per
user-facing feature (top 3–5), shaped like [feature-map](references/feature-map.md).

## 4. Prove it

Follow the generated skill once end to end: launch, doctor, drive one feature, capture evidence,
clean up, and confirm the evidence still exists. Then seed one bug and confirm `make verify` fails.
A verify skill that never ran is a draft.

## 5. Keep it honest

Run the **verify-maintain** skill after features change.
