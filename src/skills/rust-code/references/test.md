# Rust tests

*Verified with: The tests in assets/template pass (10 unit, 4 live) on Rust stable.*

Reference: `assets/template` (`#[cfg(test)]` modules, `crates/svc-api/src/tests.rs`, `crates/svc-infra/tests/live.rs`).

## Unit tests

- Beside the code in `#[cfg(test)] mod tests` (core logic) or a `tests.rs` file; test modules `#[allow(clippy::unwrap_used, clippy::expect_used)]`.
- **Table-driven:** a `struct Case { name, ... }` array and a loop with the case name in every assertion message (clippy `type_complexity` clean).
- **Fakes, not mock crates:** ports are small traits; implement them in the test (`FakeRepo(Mutex<HashMap<..>>)`, `FakeEvents`).
- **Inject time and ids** (`fn() -> OffsetDateTime`, `fn() -> String`); no `SystemTime::now()` in logic under test.
- **Config tests:** each secret required by name, one error listing every problem and no values, `Debug` hides secrets, `NAME_FILE` read,
  `env_example_is_complete` (the example loads; secrets blank).
- **Handlers:** `router().oneshot(Request)` (`tower::ServiceExt`), assert status, `error.code` and that every envelope field is present.
- **Async:** `#[tokio::test]`; wait on channels/futures with `tokio::time::timeout`, never `sleep` for a result.

## Live tests (`#[ignore]`)

Real PostgreSQL, Redis, Kafka and RustFS; ignored by default so `cargo test` stays hermetic:

```bash
docker compose -f docker-compose.infra.local.yaml up -d postgres redis kafka rustfs
scripts/health.sh --wait postgres,redis,kafka,s3              # the production readiness gate
set -a; . ./.env; set +a
cargo test -p svc-infra --features kafka -- --ignored --test-threads=1
docker compose -f docker-compose.infra.local.yaml down -v
```

| Adapter | Assert |
|---|---|
| Postgres | goose Up applies; round trip; unknown/invalid id is `NotFound`; upsert idempotent; timestamps UTC |
| Redis | second lock holder refused; only the owner releases; release frees it |
| Kafka | create the topic first, publish with a header, consume, commit only after handling |
| S3 | put/get/list/delete; missing key is `NotFound` |

Use unique names per run (`Uuid` keys, topics, groups) and `--test-threads=1` when tests share one database.

## CI

`cargo fmt --all -- --check`, `cargo clippy --workspace --all-targets --all-features -- -D warnings`, `cargo test --workspace`, `cargo deny check`
(licences/advisories) where configured, then the live job on a runner with Docker (cmake installed when Kafka is built).
Benchmarks (`criterion`) for hot paths; `cargo flamegraph` before optimising.

## Example usage

- “Add table-driven tests for the order validation rules.”
- “Write a live test for the Kafka consumer's at-least-once behaviour.”
