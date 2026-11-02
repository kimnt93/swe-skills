---
name: rust-code
description: The language for performance-critical code in this stack (hot paths, Rust cores for Python via PyO3, low-latency services). Write, change or review Rust code in this stack, including Python packages with a Rust core - new workspaces and axum services, env config and secrets, PostgreSQL (tokio-postgres raw SQL), Redis, Kafka (rdkafka), S3/RustFS (aws-sdk-s3), features, tests, and pyo3/maturin bindings with numpy and polars, wheels and releases. Use for any Rust task such as add Postgres, Redis, Kafka or S3, add an endpoint, scaffold a workspace, write tests, expose Rust to Python, move a hot path from Python to Rust or build wheels; it routes to the matching reference and carries the Rust standard (rustfmt, clippy -D warnings) and the readable-code rules (one statement per line, 100 columns, multi-line SQL).
metadata:
  group: language
  version: "1.0"
---

# Rust code

One entry point for Rust work, including Rust-backed Python packages. Read this page, then **read the references that match the request**.

**Rust is for performance:** hot paths that Go or Python can't make fast enough (matching, pricing, indicators,
parsers, large in-memory computations), Rust cores for Python packages (PyO3), and low-latency services. Bring the
baseline number that justifies it (the `benchmark-checklist` skill); new ordinary APIs are Go (`go-code`).

## How to work

1. **Discover the project first.** Read `Cargo.toml` (workspace, features, pinned versions), `AGENTS.md`/`README` and one sibling module per crate you will touch. Follow the
   project's conventions; use the defaults below for new code.
2. **Pick the topics** from the request and read the matching reference(s) ("add Postgres" = [postgres](references/postgres.md) +
   [env-config](references/env-config.md) + [feature](references/feature.md)).
3. **Implement inside-out** (core types and ports, adapter, API or binding, composition) and reuse the tested files in `assets/template` (service workspace) or
   `assets/pyrust-template` (Python extension).
4. **Write it readable.** Before you write code, read [readable-code](references/readable-code.md) and follow it for every line you add or change: one statement per line, spaces, short lines, small functions, multi-line SQL. Run the formatter, then check your own diff against its list.
5. **Verify** with the checks at the bottom; report what ran and what did not (live tests are `#[ignore]`d by default).

## Which reference to read

| The request mentions | Read |
|---|---|
| new workspace, new crate, new service, axum, layout, shutdown | [scaffold](references/scaffold.md) (tested workspace in `assets/template`) |
| which crate, standard, naming, performance, workspace rules | [stack](references/stack.md) |
| formatting, readability, long lines, clean up, review, **writing or formatting any SQL query** | [readable-code](references/readable-code.md) |
| env vars, config, secrets, `.env.example`, Loader | [env-config](references/env-config.md) |
| API contract: `/v1` versions, `/docs` Swagger, `/healthz`, `/internal` (service token + caller headers), port 3000, host `{service}.{env}.{host}`, refactor an API | the `api-contract` skill |
| Postgres, SQL, tokio-postgres, deadpool, repository | [postgres](references/postgres.md) |
| use an ORM (SeaORM / bun / SQLAlchemy), "swap to an ORM" | the `db-orm` skill (opt-in; **raw SQL is the default**) |
| migration, schema change, new column or index, goose | the `db-migrations` skill (goose SQL files) |
| Redis, cache, lock | [redis](references/redis.md) |
| Kafka, rdkafka, producer, consumer, cmake | [kafka](references/kafka.md) |
| S3, RustFS, MinIO, bucket, object | [s3](references/s3.md) |
| add a feature, use case, endpoint end to end | [feature](references/feature.md) |
| tests, `#[ignore]` live tests, clippy, CI, benchmarks | [test](references/test.md) |
| Python package with a Rust core, pyo3, maturin, abi3, layout | [pyrust-scaffold](references/pyrust-scaffold.md) (`assets/pyrust-template`) |
| expose a Rust function or class to Python, numpy, GIL, exceptions, stubs | [pyrust-binding](references/pyrust-binding.md) |
| polars DataFrame in or out of Rust, pyo3-polars | [pyrust-polars](references/pyrust-polars.md) (`assets/pyrust-polars`) |
| build wheels, CI matrix, Docker, publish, release checklist | [pyrust-release](references/pyrust-release.md) |
| logging, tracing, metrics, Dockerfile, Compose, CI deploy | the `service-logging`, `service-tracing`, `service-errors` (Sentry/GlitchTip), `data-realtime-metrics`, `deployment-setup` skills |

## Rules that always apply

- **Stack:** tokio, axum, serde, thiserror, tracing, `time`, tokio-postgres + deadpool with raw SQL (an ORM only when asked: `db-orm`), redis, rdkafka, aws-sdk-s3, polars (pinned), pyo3 (abi3) + maturin ([stack](references/stack.md)).
- **Standard:** `cargo fmt --all`, `cargo clippy --workspace --all-targets --all-features -- -D warnings`, `unsafe_code = "forbid"`, no `unwrap()`/`expect()` on external input, `///`
  docs on public items, RFC 430 naming, typed errors (`thiserror`) with stable codes and no secrets in messages.
- **Readable code, always:** one statement per line, spaces around every operator, at most 100 columns, a condition has at most two operands (more: one
  `if` per rule, each with its own error), a chain has at most three calls per line, a function fits one screen, a blank line between steps, and **SQL is written
  multi-line, one clause and one column per line**. Never compress code to save lines; `cargo fmt` is not enough ([readable-code](references/readable-code.md): bad/good examples).
- **Layers:** `core` (pure: domain, ports, use cases, config) / `infra` (adapters) / `api` (axum binary); core reads no clock and does no I/O.
- **Rust owns the logic in Python packages:** one implementation per concept in the core crate; the pyo3 crate converts types and errors only and releases the GIL (`py.detach`).
  `pyo3`, `numpy`, `pyo3-polars` and `polars` versions move as one set.
- **Environment only:** `config/` with a `Loader` and one file per infrastructure; secrets from `NAME` or `NAME_FILE` with **no default**; `Debug` hides secrets; `.env.example` is tested to load.

| Infrastructure | Variables | Example file | Config file |
|---|---|---|---|
| PostgreSQL | `POSTGRES_HOST/PORT/DB/USER/PASSWORD/POOL_SIZE` | `assets/env/postgres.env.example` | `config/postgres.rs` |
| Redis | `REDIS_HOST/PORT/DB/PASSWORD` | `assets/env/redis.env.example` | `config/redis.rs` |
| Kafka | `KAFKA_BOOTSTRAP_SERVERS/SECURITY_PROTOCOL/SASL_*/CONSUMER_GROUP` | `assets/env/kafka.env.example` | `config/kafka.rs` |
| S3 / RustFS | `S3_ENDPOINT/REGION/BUCKET/FORCE_PATH_STYLE/ACCESS_KEY/SECRET_KEY` | `assets/env/s3.env.example` | `config/s3.rs` |

The config files are `assets/template/crates/svc-core/src/config/`; copy only what the service uses.

## Verify

```bash
cargo fmt --all -- --check && cargo clippy --workspace --all-targets --all-features -- -D warnings && cargo test --workspace
docker compose -f docker-compose.infra.local.yaml up -d && scripts/health.sh --wait postgres,redis,kafka,s3          # deployment-setup templates
set -a; . ./.env; set +a; cargo test -p svc-infra --features kafka -- --ignored --test-threads=1                    # live adapters
maturin develop --release && pytest -q && pycodestyle --max-line-length=79 python tests                              # Python extension
```

## Example prompts

- "add S3 storage to this crate" -> s3, env-config · "add Postgres with raw SQL" -> postgres, feature · "consume Kafka with manual commit" -> kafka
- "move this rolling indicator from Python to Rust" -> pyrust-scaffold, pyrust-binding · "return a polars frame from Rust" -> pyrust-polars · "build wheels" -> pyrust-release
