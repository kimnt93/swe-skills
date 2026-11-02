# Rust stack

*Verified with: Workspace tested with Rust stable (1.99), axum 0.8, tokio 1, tokio-postgres 0.7, deadpool-postgres 0.14, redis 0.27, rdkafka 0.38, aws-sdk-s3 1, time 0.3; rustfmt and clippy -D warnings clean; live tests against PostgreSQL, Redis, Kafka and RustFS.*

Evidence and defaults: the data/engine repositories fix the workspace shape and libraries (`thiserror`, `tracing`, `serde`,
`time`, `parking_lot`, `arc-swap`, `blake3`, `rdkafka`, `redis`, pinned `polars`, `pyo3`); the async service defaults
(`tokio`, `axum`) are recommended here and verified by the scaffold. Follow the project's existing choice when it differs.

| Concern | Crate | Rule |
|---|---|---|
| Edition / toolchain | edition 2021+, `rust-toolchain.toml` (stable, `rustfmt`, `clippy`) | `unsafe_code = "forbid"` in `[workspace.lints]` |
| Errors | `thiserror` for library/domain enums; `anyhow` only in binaries | one enum per crate boundary, stable `code()`, no secrets in messages |
| Async runtime / HTTP | `tokio`, `axum` 0.8, `tower` | thin handlers, one envelope ([feature](feature.md)) |
| Serialisation | `serde`, `serde_json`; `time` (not `chrono`) with `serde::rfc3339` | UTC everywhere |
| Fast JSON | `sonic-rs` or `simd-json` on measured hot paths; `serde_json::value::RawValue` to forward | benchmark first; never parse what you only forward |
| Logging / tracing | `tracing` + `tracing-subscriber` (JSON), OpenTelemetry via `service-tracing` | span per boundary, fields not strings |
| PostgreSQL | `tokio-postgres` + `deadpool-postgres` (raw SQL), or `sqlx` where compile-time checking is wanted | SQL only in the infra crate ([env-config](env-config.md)) |
| Redis | `redis` with `ConnectionManager` | token-owned locks, TTLs |
| Kafka | `rdkafka` (librdkafka, `cmake-build`, needs cmake) behind a Cargo feature | idempotent producer, manual-commit consumer |
| Object store | `aws-sdk-s3` with static credentials and a custom endpoint | path-style, checksums only when required |
| DataFrames | `polars` (pinned exactly, `default-features = false`) | one version across the workspace: `cargo tree -d -i polars` prints nothing |
| Concurrency | `parking_lot`, `arc-swap`, `rayon` for CPU work | no blocking I/O under a lock |
| Hashing | `blake3` (digests), `ahash`/`hashbrown` (maps) | `BTreeMap` where output order must be deterministic |
| Python bindings | `pyo3` (abi3), `pyo3-polars`, `maturin` | [pyrust-scaffold](pyrust-scaffold.md) |
| Tests | built-in `#[test]`, `#[tokio::test]`, `#[ignore]` for live infrastructure; `criterion` for benches | ([test](test.md)) |

## Code standard (the common Rust format)

- **Format:** `cargo fmt --all` (default rustfmt, no hand formatting); CI runs `cargo fmt --all -- --check`.
- **Readable layout:** one statement per line, at most 100 columns (`rustfmt.toml`), a condition has at most two operands, a function fits one screen (clippy
  `too_many_lines`, `cognitive_complexity`), SQL constants are multi-line. `cargo fmt` is the minimum, not the goal: see [readable-code](readable-code.md) for bad/good examples.
- **Lint:** `cargo clippy --workspace --all-targets --all-features -- -D warnings`; `[workspace.lints]` enables clippy `all`, and warns on
  `unwrap_used`/`expect_used` (tests opt out with `#[allow(...)]`). Never `unwrap()`/`expect()` on external input.
- **Naming (RFC 430):** `snake_case` functions/modules/variables, `UpperCamelCase` types and traits, `SCREAMING_SNAKE_CASE` consts;
  acronyms as words (`HttpClient`, `Uuid`); conversions `as_`/`to_`/`into_`, getters without `get_`; one module per concept.
- **API guidelines:** public items have `///` docs and each module a `//!` header stating its contract; derive `Debug`, `Clone`, `PartialEq` where
  meaningful; manual `Debug` for types holding secrets; `#[must_use]` on results that matter; `pub(crate)` for internals; private fields with
  constructors that validate.
- **Errors and panics:** `Result` everywhere on I/O and parsing; panics only for programmer errors at start-up.
- **Determinism:** no `HashMap` iteration order in output, no wall clock in logic (inject time), UTC `time::OffsetDateTime`.
- **Environment:** one `config` module loads everything through a `Loader` (every missing variable listed by name, never a value); secrets come
  from `NAME` or `NAME_FILE` with **no default**; `.env.example` is tested to load ([env-config](env-config.md)).
- **Workspace:** `[workspace.dependencies]` for every version, members use `dep.workspace = true`; `core` (pure) / `infra` (adapters) / `api`
  (binary) split; features gate optional heavy deps (Kafka, Postgres in a data crate).
- **Build profiles:** `[profile.dev] debug = "line-tables-only"`, `[profile.test] debug = 0`, `[profile.release] lto = "thin"`.

## Performance

Measure with `criterion` and `cargo flamegraph` before tuning; borrow instead of clone (`&str`, `Cow`), `Vec::with_capacity`, avoid per-item
allocation and logging in hot loops, `bytes::Bytes` for shared buffers, `rayon` for data-parallel CPU work, SIMD JSON only where profiling shows
parsing dominates.

## Related skills

[readable-code](readable-code.md) · [scaffold](scaffold.md) · [env-config](env-config.md) · [feature](feature.md) ·
[test](test.md) · [pyrust-scaffold](pyrust-scaffold.md) · `deployment-setup` (cmake in the build stage when Kafka is used) ·
`service-logging` · `service-tracing`.

## Example usage

- “Which crates should this new Rust service use?”
- “Add the Postgres and S3 adapters to this crate with env-based config.”
