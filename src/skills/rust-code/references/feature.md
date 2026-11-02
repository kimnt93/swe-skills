# Rust feature

Read the neighbouring module in each crate first; write what reads like it. Work inside-out.

## Order of work

1. **Contract:** inputs, outputs, error cases, idempotency, concurrency (replicas, tasks), money/time units. Cite external rules in a comment.
2. **Core domain** (`svc-core`): the rule as pure code with a typed error variant (`#[derive(thiserror::Error)]`, stable `code()`), unit tests in a
   `#[cfg(test)]` module. No I/O crates, no clock (take `OffsetDateTime` as a parameter), no `HashMap` iteration order in output (`BTreeMap`).
3. **Port and use case:** a small `trait` declared in core (`async fn` in trait; generic use case `Items<R, E>`, no boxing); the use case
   owns flow and validation. Test with hand-written fakes (`Mutex<HashMap<...>>`).
4. **Adapter** (`svc-infra`): implement the trait with raw SQL / SDK calls; map driver errors to the core error without leaking text; schema
   change = a new goose file, never an edit of a released one; idempotent writes (`ON CONFLICT`).
5. **API** (`svc-api`): extract with axum, call one use case, answer through the envelope (`Result<Response, ApiError>`); map the new error
   variant to a status and stable code in `ApiError::into_response`; authenticate before trusting identity headers (constant-time compare).
6. **Compose** in `main.rs` only. **Config:** new settings go through the `Loader` ([env-config](env-config.md)) and `.env.example`.
7. **Tests** ([test](test.md)): core unit tests, handler tests with `tower::ServiceExt::oneshot`, `#[ignore]` live tests for SQL, locks, Kafka.
8. **Observability:** `tracing` fields (`code`, ids), never secrets/payloads; spans for outbound calls (`service-tracing`).

## Cross-cutting checks

- No `unwrap()`/`expect()` on external input (clippy warns); errors carry context but no secrets; `?` with `From` conversions at crate edges.
- `async`: never hold a `std::sync::Mutex`/`parking_lot` guard across `.await`; no blocking calls inside async (use `spawn_blocking` or a dedicated thread);
  spawned tasks have an owner and a shutdown path.
- Prefer borrowing (`&str`, slices) in APIs; clone deliberately; `Vec::with_capacity` when the size is known.
- A new dependency? check [stack](stack.md) first; heavy optional ones go behind a feature.

## Verify

```bash
cargo fmt --all -- --check && cargo clippy --workspace --all-targets --all-features -- -D warnings && cargo test --workspace
set -a; . ./.env; set +a; cargo test -p svc-infra --features kafka -- --ignored --test-threads=1   # when SQL/Redis/Kafka/S3 behaviour changed
```

## Example usage

- “Add cancel-order: domain rule, use case, Postgres update, endpoint and tests.”
- “Add a Kafka consumer that is safe to replay.”
