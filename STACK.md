# Dev stack

The stack the `swe` skills assume. Each row names the choice and the skill that holds the rules. When a project
differs, its `PROJECT.md` and `ARCHITECTURE.md` win; the skills say so where it matters.

## Languages: one job each

| Job | Language | Why | Skill |
|---|---|---|---|
| HTTP APIs and backend services | **Go** with Fiber v3 | one static binary, simple concurrency, fast to build and deploy | `go-code` |
| ML, data, feature pipelines, model serving | **Python 3.11+** | the ML ecosystem; Litestar for services | `py-code` |
| Performance-critical cores | **Rust** (axum; PyO3 + maturin for Python cores) | predictable latency, memory safety | `rust-code` |
| Web apps and dashboards | **TypeScript**: Next.js (App Router) or Vite + React | server-rendered apps, or SPAs for internal tools | `ts-code` |

Router rule: Go unless the task is ML or data (Python) or a measured hot path (Rust). See `swe`.

## Data and messaging

| Concern | Choice | Notes |
|---|---|---|
| Database | **PostgreSQL** | raw SQL by default (go-pg v10, psycopg 3, tokio-postgres); multi-line SQL, bounded lists |
| ORM | **go-pg v10** (Go only) | only when asked or already present (`db-orm`); Python and Rust stay on raw SQL |
| Migrations | **goose** SQL files, run by a one-shot job | `db-migrations`; expand and contract for risky changes |
| Cache | **Redis** (go-redis v9, redis-py, redis-rs) | |
| Streaming | **Kafka** (confluent-kafka-go v2, confluent-kafka, rdkafka) | idempotent consumers (`principles`) |
| Object storage | **S3 API on RustFS** (AWS SDK v2, boto3, aws-sdk-s3) | |
| Dataframes | **polars** (not pandas) | |
| JSON and time | msgspec, orjson, ciso8601 (Python) | no pydantic |

## Data engineering

| Concern | Choice | Skill |
|---|---|---|
| Realtime pipelines | **Pathway**: Kafka in, windows and joins, Kafka or database out | `data-pathway` |
| Batch and scheduled pipelines | **Dagster** assets, partitions, asset checks, schedules | `data-dagster` |
| Pipeline metrics | one OTel set, `stream_pipeline_*` for streams and `dagster_*` for jobs | `data-realtime-metrics` |
| Dashboards | Grafana JSON checked against the metrics the code emits | `data-pathway`, `data-dagster` |

## Platform

| Concern | Choice | Skill |
|---|---|---|
| Packaging and deploy | **Docker**, **Docker Swarm** stacks, **Traefik** routing by Host rule and labels | `deployment-setup` |
| HTTP contract | `/v1` versions, Swagger at `/docs`, `/healthz`, port 3000, `x-internal-service-token` | `api-contract` |
| CI | **GitHub Actions**; `make verify` is the one required check | `verify-create`, `github` |
| Source control | GitHub, trunk on `main`, squash-only PRs, Conventional Commits | `github` |
| Change logs | `CHANGELOG.md` per repo in the PR; `changelog/` in the project directory | `changelog` |

## Observability

| Signal | Choice | Skill |
|---|---|---|
| Logs | structured JSON (zerolog, jlogger, pino, tracing) to **Loki** | `service-logging` |
| Traces | **OpenTelemetry** (OTLP), service graph first | `service-tracing` |
| Metrics | OTel to **Mimir** / Prometheus, **Grafana** | `data-realtime-metrics` |
| Errors | **Sentry** or **GlitchTip** through the DSN, nothing private sent | `service-errors` |

## Quality

| Concern | Choice | Skill |
|---|---|---|
| Formatting and lint | gofmt + goimports + golangci-lint; ruff and PEP 8 (79); rustfmt + clippy `-D warnings`; ESLint | language skills |
| Tests | tests first for bugs; Go `testing`, pytest, `cargo test`, Vitest + Testing Library, Playwright | `tdd` |
| Money paths | replay of a recorded day against a golden file; formal checks for state machines | `replay-test`, `formal-verify` |
| Review | a different model family reviews; findings are proven by a run | `interrogate` |

## Agents

| Concern | Choice |
|---|---|
| Harnesses | Claude Code, Codex, oh-my-pi as plugins; 50+ more as plain skills (`make harness`) |
| Project runner | `swe-cli`: YAML workflows, one agent per node, tmux or Orca, one git worktree per card |
| Roles | manager, planner, developer, reviewer, documenter, intake, integrator, ci-fixer, verifier, scribe |
| Model tiers | top for review and design, mid for building, low for docs and changelog (`models.yaml`) |

Change this file in the same PR as the choice it describes.
