# Rust

Template: `assets/templates/rust/service_tracing.rs` (a module) with `main.rs` (tests + demo) and `Cargo.toml`.
Tested with opentelemetry / opentelemetry_sdk / opentelemetry-otlp 0.33 (`cargo test`). Match the API, SDK,
exporter and the `tracing-opentelemetry` bridge versions from the project's lockfile; these are not pins.

```toml
opentelemetry = "0.33"
opentelemetry_sdk = "0.33"
opentelemetry-otlp = { version = "0.33", default-features = false, features = ["trace", "http-proto", "reqwest-blocking-client"] }
gethostname = "1"
```

Blocking `reqwest` is deliberate: the batch processor runs on its own thread, so it works under any runtime.

## Wire it

```rust
let tracing = Tracing::from_env()?;      // OTEL_SERVICE_NAME|SERVICE_NAME, RUN_ENV, OTEL_* (references/env.md)
// ... run ...
tracing.shutdown();                       // flushes within the exporter timeout; keep the handle for this
```

Build it once at startup. If the service already uses `tracing` + a subscriber, extend that subscriber with
`tracing_opentelemetry::layer().with_tracer(...)` instead of installing a second global subscriber, and use
the helpers only for boundaries the bridge does not cover.

## Boundary spans (dependency mode)

Each `*_context` helper starts a span and returns the `Context` holding it; call `finish(&cx, err)` once.

| Hop | Use |
|---|---|
| Inbound HTTP (axum/actix) | `axum-tracing-opentelemetry` / `tracing-actix-web`, or `server_context("POST /orders", &Carrier::from_pairs(headers))` |
| Outbound HTTP (reqwest) | `client_context(&cx, "GET /pricing", "pricing", &mut out)`, then send `out.0` as headers (or `opentelemetry-http::HeaderInjector`) |
| PostgreSQL / Redis / ClickHouse / S3 | `peer_context(&cx, "postgres", "select orders")` around the call |
| Kafka (`rdkafka`) | `producer_context(&cx, topic, &mut carrier)`, copy the carrier into `OwnedHeaders`; `consumer_context(topic, &Carrier::from_pairs(headers))` per message |

## Rules and pitfalls

- **Async**: never hold `cx.attach()`'s guard across `.await` (it leaks context into other tasks). Use
  `fut.with_context(cx.clone())` (`opentelemetry::trace::FutureExt`) and call `finish` after the future completes.
- `finish(&cx, Some(&err))` records the error **type name** only. `detail_context` returns `None` unless
  `TRACING_DETAIL=true`: `if let Some(cx) = tracing.detail_context(&parent, "compute") { ...; tracing.finish::<String>(&cx, None); }`.
- Log correlation: `Tracing::ids(&cx)` gives `(trace_id, span_id)` hex or empty strings; log both or neither.
- Match exporter features and runtime: `reqwest-blocking-client` for a thread-based batch processor; async
  clients need the matching runtime feature on the SDK.

Source: [Rust documentation](https://opentelemetry.io/docs/languages/rust/).

## Example usage

- “Add dependency tracing to this axum service and its Kafka consumer.”
