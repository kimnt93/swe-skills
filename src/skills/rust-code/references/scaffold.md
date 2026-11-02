# Rust scaffold

*Verified with: formatted with rustfmt, clippy -D warnings clean (all features), 10 unit tests and 4 live tests (PostgreSQL, Redis, Kafka, RustFS) passing on Rust stable.*

Start from `assets/template`; it encodes [stack](stack.md) and passes its checks.

## Layout

```text
Cargo.toml              [workspace] members crates/*; [workspace.dependencies], [workspace.lints], profiles
rust-toolchain.toml     stable + rustfmt + clippy
.env.example            every variable the config reads; secrets blank
schemas/                goose SQL migrations (immutable once released)
crates/svc-core/        PURE: item (domain), ports (traits), service (use cases), error, config/ (Loader + postgres redis kafka s3)
crates/svc-infra/       adapters implementing ports: postgres.rs, redis_lock.rs, s3.rs, kafka.rs (feature "kafka"); tests/live.rs (#[ignore])
crates/svc-api/         axum binary: app.rs (router, auth), envelope.rs (response + error mapping), main.rs (composition + shutdown)
```

Dependencies point inward: `svc-api -> svc-core <- svc-infra`; `svc-core` imports no I/O crates and reads no clock.

## Steps

1. Copy `assets/template/.`; rename `svc-*` crates and the sample `item`; `cp .env.example .env` and fill the blank secrets.
2. Delete adapters and config modules you do not use (and their lines in `config/mod.rs`). Kafka is behind `--features kafka` because
   `rdkafka` builds librdkafka with **cmake**: install `cmake` in CI and in the Docker build stage only when Kafka is used.
3. The API follows the [api-contract](../../api-contract/SKILL.md) skill: port 3000 (`PORT`), routes under `/v1`, Swagger at `/docs`
   (`docs.rs`, `#[utoipa::path]` on each handler and listed in `ApiDoc`), and `/healthz` (`health.rs`) at the root, outside the
   `/v1` auth layer; a failed check gives 503. There is no `/readyz` and no `/v1/healthz`.
4. Add deployment with `deployment-setup` (Dockerfile.rust, Swarm/local compose, `health.sh`, `HEALTH_DEPS`) and tracing with `service-tracing`.

## Checks

```bash
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace
docker compose -f docker-compose.infra.local.yaml up -d postgres redis kafka rustfs && scripts/health.sh --wait postgres,redis,kafka,s3
set -a; . ./.env; set +a; cargo test -p svc-infra --features kafka -- --ignored --test-threads=1
```

## Rules baked in

- Config fails by variable name (all problems at once), secrets have no default and come from `NAME` or `NAME_FILE`, `Debug` hides them,
  and `.env.example` is tested to load.
- Handlers extract, call one use case, answer through the envelope; the envelope always carries every field (`data` null, `error` zero
  object); only the core error's code and a generic message leave the process.
- `Result<_, ApiError>` with a small enum error type (clippy `result_large_err` clean); infrastructure errors are logged, never returned.
- Graceful shutdown on SIGTERM/Ctrl-C (`axum::serve(...).with_graceful_shutdown`); producers `flush()` before exit.
- No `unsafe`; `unwrap`/`expect` warned in non-test code.

## Example usage

- “Scaffold a Rust axum service with Postgres and S3 in our stack.”
- “Add a Kafka consumer crate to this workspace.”
