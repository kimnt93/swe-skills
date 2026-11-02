# Python scaffold

*Verified with: installed with uv; ruff and pycodestyle clean at 79 columns; 24 unit tests and 4 integration tests (live PostgreSQL, Redis, Kafka, RustFS) passing on Python 3.12.*

Start from `assets/template` instead of a blank directory: it already encodes the stack
([stack](stack.md)) and the layering rules, and it passes its tests.

## Layout

```text
pyproject.toml            uv + hatchling, ruff, pytest (integration marker excluded by default)
schemas/                  goose SQL migrations (immutable once released)
src/service/
  settings/               the only readers of environment variables: _base.py (NAME_FILE secrets), postgres.py redis.py kafka.py s3.py,
                          __init__.py composes Settings; SecretStr, no defaults for passwords
  domain/                 pure rules and value types: no I/O, no framework, no logging, no clock reads
  application/            use cases + ports (typing.Protocol declared where used); imports domain only
  db/ messaging/          adapters: psycopg pool (SQL here only), redis-py, boto3 (S3/RustFS), confluent-kafka
  api/                    app.py (factory, lifespan, middleware), routes/, envelope.py, schemas.py, deps.py
  observability/          service_logging.py (copied from the service-logging skill)
  cli.py                  `service serve` (add `worker`, `consume` as separate processes)
tests/                    unit (fakes, TestClient) + test_integration.py (real infrastructure)
```

Dependencies point inward: `api -> application -> domain`; `db`/`messaging` implement application ports.

## Steps

1. Copy `assets/template/.` into the new repository; rename the package (`service` -> your name) in `pyproject.toml`,
   imports and `[project.scripts]`; update `SERVICE_NAME` in `.env.example`.
2. Delete adapters the service does not use (`messaging/`, `db/redis.py`, ...) with their lines in `app.py`, `settings.py`
   and `.env.example`.
3. Rename the sample `item` aggregate or keep it as the pattern for the first feature ([feature](feature.md)).
4. `uv sync`, `cp .env.example .env`, fill the blank secrets (no defaults for passwords), run the checks.
5. Deployment with `deployment-setup` (Dockerfile.python, Swarm/local Compose, `health.sh`, `HEALTH_DEPS`, a `migrate`
   one-shot job); tracing with `service-tracing`; metrics with `data-realtime-metrics` for pipelines.

## Checks

```bash
uv run ruff format --check src tests && uv run ruff check src tests    # PEP 8 at 79 columns (E W F I N ...)
pycodestyle --max-line-length=79 --exclude=service_logging.py src tests   # the reference PEP 8 checker
uv run pytest                      # unit tests, no infrastructure needed
# with real infrastructure (deployment-setup/assets/templates/docker-compose.infra.local.yaml):
docker compose -f docker-compose.infra.local.yaml up -d postgres redis kafka rustfs
scripts/health.sh --wait postgres,redis,kafka,s3
set -a; . ./.env; set +a; uv run pytest -m integration -o addopts=""
```

## Rules baked into the template

- **PEP 8 everywhere:** 79 columns, `snake_case`, exceptions end in `Error`, imports sorted, docstrings wrapped; the template passes ruff
  and pycodestyle with zero findings.
- Settings fail by variable name; secrets are `SecretStr`, never in `repr`/logs; a missing password is an error; `.env.example` is
  tested to load (`test_env_example_is_complete`) and keeps every secret blank.
- Routes only validate, call one use case and answer through the envelope (same JSON contract as the Go and Rust services: every field always present, `data` null and
  `error` `{"code": "", "retryable": false}` when unused);
  domain failures are registered handlers, anything else is logged and returned as a generic 500.
- The API follows the [api-contract](../../api-contract/SKILL.md) skill: port 3000, routes under `/v1`, Swagger at `/docs`, and
  `/healthz` (identity, `api_versions`, non-secret config, one check per required dependency within 2 s; 503 when one is down), at the
  root and not under `/v1`. There is no `/readyz`; add `"v2"` to `api/versions.py` for a second version.
- Shutdown on SIGTERM: uvicorn graceful (15 s), then the lifespan closes the pool, Redis and the producer (drains).
- The Kafka producer polls on a thread and resolves an asyncio Future from the delivery callback; the consumer polls in an
  executor, commits after the handler, and always closes (leaves the group cleanly).
- One process per command; `uvicorn --factory` with `log_config=None` so jlogger owns the output.

## Example usage

- “Scaffold a new Litestar service for pricing in our Python stack.”
- “Start a Kafka-consumer worker with the same layout.”
