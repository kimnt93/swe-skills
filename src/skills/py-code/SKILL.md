---
name: py-code
description: The language for ML and data in this stack (training, evaluation, inference, feature pipelines, dataframes), plus Python services that serve a model or data in process. Write, change or review Python code - ML pipelines, Litestar APIs (msgspec, never pydantic), PostgreSQL (psycopg 3 plain SQL), Redis, Kafka (confluent-kafka), S3/RustFS (boto3), env settings and secrets, Celery and Kafka workers, fast JSON and timestamps (msgspec, orjson, ciso8601), polars instead of pandas, features, tests and refactors, all at PEP 8 (79 columns) and the readable-code rules (one statement per line, multi-line SQL). Use for any Python task such as add Postgres or Redis, consume Kafka, store files in S3, add an endpoint, speed up JSON or dataframe code, scaffold a service, write tests or refactor; it routes to the matching reference.
metadata:
  group: language
  summary: "ML and data in Python: polars, msgspec, and Litestar to serve a model"
  version: "1.0"
---

# Python code

One entry point for Python work. Read this page, then **read the references that match the request** before writing code.

**Python is for ML and data.** New HTTP APIs are Go/Fiber (`go-code`); use Litestar only to serve a Python model or
data endpoint in process. A measured hot loop moves to Rust through PyO3 (the pyrust references in `rust-code`).

## How to work

1. **Discover the project first.** Read `pyproject.toml`, `AGENTS.md`/`README`, the package layout and one sibling module per layer you will touch. Follow the
   project's conventions; use the defaults below for new code.
2. **Pick the topics** from the request and read the matching reference(s) (several usually apply: "add Postgres to this service" =
   [postgres](references/postgres.md) + the environment section below + [feature](references/feature.md)).
3. **Implement inside-out** (domain, application port, adapter, route, composition) and reuse the tested files in `assets/template` rather than writing
   adapters from scratch.
4. **Write it readable.** Before you write code, read [readable-code](references/readable-code.md) and follow it for every line you add or change: one statement per line, spaces, short lines, small functions, multi-line SQL. Run the formatter, then check your own diff against its list.
5. **Verify** with the checks at the bottom; report what ran and what did not.

## Which reference to read

| The request mentions | Read |
|---|---|
| new service, new project, "start", layout, settings, uv, pyproject | [scaffold](references/scaffold.md) (tested skeleton in `assets/template`) |
| which library, stack, PEP 8, async rules, naming | [stack](references/stack.md) |
| ML, model, training, evaluation, features, inference, notebook, scikit-learn, LightGBM, PyTorch, backtest split | [ml](references/ml.md) (+ [data](references/data.md)) |
| Litestar, endpoint, route, schema, dependency, middleware, error handler (serving a model or data in process; new APIs are Go) | [litestar-api](references/litestar-api.md) |
| API contract: `/v1` versions, `/docs` Swagger, `/healthz`, `/internal` (service token + caller headers), port 3000, host `{service}.{env}.{host}`, refactor an API | the `api-contract` skill |
| Postgres, SQL, psycopg, repository, migration, goose, pool | [postgres](references/postgres.md) |
| migration, schema change, new column or index, goose | the `db-migrations` skill (goose SQL files) |
| Redis, cache, lock, TTL, idempotency | [redis](references/redis.md) |
| Kafka, topic, consumer, producer, stream | [kafka](references/kafka.md) |
| S3, RustFS, MinIO, boto3, bucket, object, file, artifact | [s3](references/s3.md) |
| formatting, readability, long lines, clean up, review, **writing or formatting any SQL query** | [readable-code](references/readable-code.md) |
| JSON, msgspec, orjson, timestamps, polars, pandas, dataframe, performance | [data](references/data.md) (+ `scripts/bench.py`) |
| Celery, background job, scheduled task, worker process, queue | [worker](references/worker.md) |
| add a feature, use case, business rule end to end | [feature](references/feature.md) |
| tests, pytest, fixtures, integration test, CI | [test](references/test.md) |
| refactor, clean up, restructure, split a module, replace pandas | [refactor](references/refactor.md) |
| Rust for speed, pyo3, maturin, native extension, wheels | the Rust references: [pyrust-scaffold](../rust-code/references/pyrust-scaffold.md), [pyrust-binding](../rust-code/references/pyrust-binding.md), [pyrust-polars](../rust-code/references/pyrust-polars.md), [pyrust-release](../rust-code/references/pyrust-release.md) |
| logging, tracing, metrics, Dockerfile, Compose, CI deploy | the `service-logging`, `service-tracing`, `service-errors` (Sentry/GlitchTip), `data-realtime-metrics`, `deployment-setup` skills |

## Rules that always apply

- **Stack:** uv, ruff, Litestar + uvicorn, msgspec at the edges, psycopg 3 (plain SQL, no ORM), redis-py asyncio, confluent-kafka, boto3, Celery, polars
  (not pandas), msgspec / orjson / ciso8601 for hot paths ([stack](references/stack.md)).
- **PEP 8, enforced:** 79 columns, `snake_case` / `CapWords` / `UPPER_CASE`, exception names end in `Error`, imports sorted, docstrings wrapped; `ruff format`,
  `ruff check` (`E W F I N UP B SIM ASYNC`) and `pycodestyle --max-line-length=79` must be clean.
- **Readable code, always:** one statement per line (no `;`, no `if x: y`), spaces around every operator, 79 columns, a condition has at most two operands (more: one
  `if` per rule, each with its own error), a chain has at most three calls per line, a function fits one screen, a blank line between steps, and **SQL is written
  multi-line in a triple-quoted constant, one clause and one column per line**. Never compress code to save lines ([readable-code](references/readable-code.md): bad/good examples).
- **Async is a contract:** nothing blocking in `async def` (async clients, `asyncio.to_thread` for boto3, executors for confluent-kafka polling).
- **No pydantic, ever** (and so no FastAPI, which cannot run without it, and no pydantic-settings). Layering enforced by `lint-imports` (import-linter contracts in the template's `pyproject.toml`). Enforced by ruff `TID251` in the template's
  `pyproject.toml`, which also bans `pandas` (use polars); **Typed boundaries:** `msgspec.Struct` for API models and messages, frozen dataclasses in the domain, a dataclass loaded from the environment for settings; UTC-aware datetimes; no per-row Python in data paths.
- **Layers:** `api -> application -> domain`; adapters implement ports; domain does no I/O and reads no clock.
- **Environment only:** a `settings/` package, one module per infrastructure; secrets are `SecretStr` read from `NAME` or `NAME_FILE` with **no default**; `.env.example`
  lists everything with secrets blank and a test proves it loads.

| Infrastructure | Variables | Example file | Settings module |
|---|---|---|---|
| PostgreSQL | `POSTGRES_HOST/PORT/DB/USER/PASSWORD/SSLMODE/POOL_SIZE` | `assets/env/postgres.env.example` | `settings/postgres.py` |
| Redis | `REDIS_HOST/PORT/DB/PASSWORD` | `assets/env/redis.env.example` | `settings/redis.py` |
| Kafka | `KAFKA_BOOTSTRAP_SERVERS/SECURITY_PROTOCOL/SASL_*/CONSUMER_GROUP` | `assets/env/kafka.env.example` | `settings/kafka.py` |
| S3 / RustFS | `S3_ENDPOINT/REGION/BUCKET/FORCE_PATH_STYLE/ACCESS_KEY/SECRET_KEY` | `assets/env/s3.env.example` | `settings/s3.py` |

The settings modules are `assets/template/src/service/settings/` (`_base.py` plus one file per infrastructure); copy only what the service uses.

## Verify

```bash
uv run ruff format --check src tests && uv run ruff check src tests && pycodestyle --max-line-length=79 src tests
uv run pytest
docker compose -f docker-compose.infra.local.yaml up -d && scripts/health.sh --wait postgres,redis,kafka,s3        # deployment-setup templates
set -a; . ./.env; set +a; uv run pytest -m integration -o addopts=""                                                # live adapters
```

## Example prompts

- "add using pg db" / "add a repository for orders with a bounded query" -> postgres, feature
- "consume the ticks topic and decode fast" -> kafka, data · "make this pandas job faster" -> data · "store reports in RustFS" -> s3
- "add a Celery task that retries" -> worker · "scaffold a Litestar service" -> scaffold
