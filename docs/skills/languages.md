# Language skills

One skill per language, each a short router: it discovers the project, picks the references that match the
request, builds inside-out from tested templates in `assets/`, writes it readable, and verifies. Pick by the
job (the router does it for you):

| The job | Skill |
|---|---|
| HTTP APIs, services, Kafka consumers, workers | `go-code` (Go with Fiber v3, the default) |
| ML and data | `py-code` |
| hot paths, Rust cores for Python | `rust-code` |
| web frontends | `ts-code` (Next.js or Vite + React) |

All four share these habits: follow what the project already does before using the defaults; one config
module and secrets only from `NAME` or `NAME_FILE` with no default; layers `interfaces to application to
domain` with adapters implementing ports; raw SQL by default (an ORM only when asked, see `db-orm`); readable
code (one statement per line, short functions, multi-line SQL); report what ran and what did not.

### go-code

**What it is.** The default for every new HTTP API, service, Kafka consumer and worker. **Stack.** Fiber v3,
go-pg v10 with raw SQL, go-redis v9, confluent-kafka-go v2, AWS SDK v2 for S3/RustFS, zerolog, goose,
OpenTelemetry. **Use it when** you add an endpoint, a Postgres/Redis/Kafka/S3 adapter, scaffold a service,
write tests or refactor Go. **Say.** `/swe:go-code consume the orders topic and upsert into Postgres,
at-least-once`.

**What happens.**
1. Read `go.mod`, the layout and one sibling file per layer.
2. Pick references: `scaffold`, `stack`, `fiber-api`, `postgres`, `redis`, `kafka`, `s3`, `feature`, `test`,
   `refactor`, `readable-code`.
3. Build inside out (domain, application port, adapter, handler, composition) from `assets/template`.
4. Verify: `golangci-lint fmt --diff` and `run`, `go test -race`, the e2e tests against live infra.

**Rules enforced, not just written.** Data structs have value fields, no pointers, no `omitempty`
(`scripts/structcheck`, escape: `//structcheck:allow <reason>`); imports respect the layers
(`scripts/archcheck`: the domain imports no I/O, `application` imports only the domain, only `bootstrap`,
`cmd` and `e2e` wire everything); lines at most 100 columns, a condition at most two operands, SQL multi-line.
**Files.** `scripts/structcheck`, `scripts/archcheck` (Go, with tests), `assets/template` (a complete service:
`cmd/api`, `internal/{domain,application,infrastructure,interfaces,bootstrap,config,e2e}`, schemas, Makefile,
`.golangci.yml`), `assets/env` (Postgres, Redis, Kafka, S3 variable examples).

### py-code

**What it is.** The language for ML and data, plus Python services that serve a model in process. New HTTP
APIs are Go. **Stack.** uv, ruff, Litestar + uvicorn, msgspec at the edges, psycopg 3 with plain SQL,
redis-py asyncio, confluent-kafka, boto3, Celery, polars (never pandas). **Use it when** you train or
evaluate a model, build a feature or data pipeline, serve a model, or work with dataframes.
**Say.** `/swe:py-code train a model for next-hour volume per symbol`.

**ML reference (`ml`).** Layout `data`, `features`, `split`, `train`, `evaluate`, `artefact`, `serve`;
splits by time (train on the past, validate on the next window, test on a later one); features at time t use
only data before t; every hyperparameter and the data snapshot id in a config, every seed set, dependencies
locked; a model card saved with the model (commit, config, snapshot, row counts, split boundaries, metrics,
library versions); a model ships only if it beats the current one on the test window; serve through a batch
worker, a small Litestar service called by the Go API, or an ONNX export in Go or Rust. Tests: feature
functions on tiny frames (NaN, empty, one row), no look-ahead, a tiny train-and-evaluate run in CI, a golden
metric, serving equals training.

**Rules enforced.** PEP 8 at 79 columns; ruff with `TID251` bans `pydantic` and `pandas` (the message names
msgspec and polars); import-linter contracts enforce `api, db, messaging` above `application` above `domain`
and "the domain does no I/O" (`lint-imports`). Nothing blocking in `async def`. **Files.** `scripts/bench.py`,
`assets/template` (a service with settings, db, messaging, observability, tests), `assets/env`.

### rust-code

**What it is.** Performance. Hot paths Go or Python cannot make fast enough (matching, pricing, indicators,
parsers), Rust cores for Python packages through PyO3, and low-latency services. Bring the baseline number
that justifies Rust. **Stack.** tokio, axum, serde, thiserror, tracing, tokio-postgres + deadpool with raw
SQL, redis, rdkafka, aws-sdk-s3, polars (pinned), pyo3 (abi3) + maturin. **Use it when** a measured hot path
moves to Rust, or you build a Python extension. **Say.** `/swe:rust-code move this rolling indicator to Rust
and expose it to Python`.

**Rules.** `cargo fmt`, `clippy --all-targets --all-features -D warnings`, `unsafe_code = "forbid"`, no
`unwrap`/`expect` on external input, typed errors with stable codes. The core crate is pure (no clock, no I/O);
adapters live in `infra`; the PyO3 crate only converts types and errors and releases the GIL. `pyo3`, `numpy`,
`pyo3-polars` and `polars` versions move as one set. Live tests are `#[ignore]`d by default.
**Python-with-Rust references.** `pyrust-scaffold`, `pyrust-binding`, `pyrust-polars`, `pyrust-release`
(wheels, CI matrix, publishing). **Files.** `assets/template` (service workspace), `assets/pyrust-template`,
`assets/pyrust-polars`, `assets/env`.

### ts-code

**What it is.** Frontends. **Next.js 16 (App Router)** for server-rendered apps and a backend-for-frontend;
**Vite 8 + React 19 + TypeScript** for dashboards and internal single-page apps. **Use it when** you scaffold
an app, add a page or component, call an API, fix a UI bug, write UI tests or set up the frontend build and
deploy. **Say.** `/swe:ts-code add an orders page that lists open orders and lets me cancel one`.

**What happens.** Discover the repo (lockfile, `tsconfig`, router, API client); generate types from the Go
service's `/docs/openapi.json` (`npm run api:types`); build inside out (API client, data hook or server
function, components, route); verify with `npm run typecheck && lint && test && build`, then `npm run e2e`
(Playwright against the production build).

**Rules.** Strict TypeScript (`noUncheckedIndexedAccess`; no `any`, no `@ts-ignore`; `console` is a lint error);
server state in React Query (Vite) or server components (Next.js); the response envelope is unwrapped once in
the API client so components get data or a typed `ApiError`; money stays a string, formatted with `Intl`;
secrets never reach the browser (only `NEXT_PUBLIC_*` or `VITE_*` are public). TypeScript is pinned to 6.0
because `typescript-eslint` does not yet support 7. **References.** `stack`, `nextjs`, `vite-react`,
`api-client`, `testing`, `readable-code`, `deploy`. **Files.** `assets/vite-react` and `assets/nextjs`:
complete templates that install from their lockfile and pass typecheck, lint, unit tests, build, Playwright,
and build into Docker images that answer `/healthz` on port 3000.
