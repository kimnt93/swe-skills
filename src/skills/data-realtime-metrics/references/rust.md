# Rust

Template: `assets/templates/rust/pipeline_metrics.rs` (add as a module). Smoke binary: `main.rs`;
dependencies: `Cargo.toml` (same folder).

Tested with Rust 1.99, `opentelemetry` / `opentelemetry_sdk` / `opentelemetry-otlp` 0.33. The
OpenTelemetry Rust API still changes between 0.x releases: pin the versions and rebuild the
smoke test after any bump.

```toml
gethostname = "1"
opentelemetry = "0.33"
opentelemetry_sdk = "0.33"
opentelemetry-otlp = { version = "0.33", default-features = false, features = ["metrics", "http-proto", "reqwest-blocking-client"] }
```

## Wire it

```rust
mod pipeline_metrics;
use pipeline_metrics::{Options, PipelineMetrics};

let token = std::env::var("OTEL_AUTH_TOKEN_FILE").ok()
    .and_then(|p| std::fs::read_to_string(p).ok()).map(|s| s.trim().to_string())
    .or_else(|| std::env::var("OTEL_AUTH_TOKEN").ok()).unwrap_or_default();
let metrics = Arc::new(PipelineMetrics::new(Options {
    service: std::env::var("SERVICE_NAME")?,        // e.g. ssi-ws-v3-transform
    environment: std::env::var("DEPLOYMENT_ENVIRONMENT").unwrap_or("local".into()),
    endpoint: std::env::var("OTEL_EXPORTER_OTLP_ENDPOINT").unwrap_or_default(),
    token,
    ingestion: false,                                // true for feed -> Kafka services
    ..Default::default()
})?);
// on exit (also from a signal handler): metrics.shutdown();
```

With `rdkafka` (producer, ingestion or transform): keep the arrival `Instant`, await the
`FutureProducer::send` result, then
`metrics.published(payload.len() as u64, arrived.elapsed())`; on `Err` call `metrics.error()`.
`metrics.set_in_flight({ let p = producer.clone(); move || p.in_flight_count() as i64 })`.
Consumer: `metrics.received(true)` per message (Kafka timestamp via `message.timestamp()`),
`dropped()` for deliberate discards, `published(..)` after the write.
Health probe (thread or task, every 5 s): `producer.client().fetch_metadata(Some(topic), timeout)`
-> `set_kafka_healthy(ok)`. Lag: `consumer.fetch_watermarks(topic, partition, timeout)` minus the
last processed offset, summed -> `set_backlog`.

Feed connection: `set_connected(true)` after the handshake, `false` on close, `reconnect()` per
retry, `set_backlog(move || rx_len())` for the internal queue depth.

## Gotchas

- Use the blocking reqwest client feature (`reqwest-blocking-client`): the periodic reader runs
  on its own OS thread, not on your async runtime. With tokio, still create the provider
  outside any `block_on` section to avoid nested runtime panics.
- `with_endpoint` for HTTP takes the full URL including the signal path; the template appends
  `/v1/metrics`. Set the protocol to `HttpBinary` explicitly.
- Boundaries are set with `.with_boundaries(...)` on the histogram builder; no unit.
- Observable gauges keep their callbacks alive after the builder handle is dropped (the
  template relies on this). The callbacks must not block: read atomics only.
- `shutdown()` ignores flush errors by design; log them if you need to.

## Verify

```bash
python3 scripts/otlp_check.py --role ingestion --wait 40 &
cp -r assets/templates/rust /tmp/rust-smoke && cd /tmp/rust-smoke \
  && mkdir src && mv main.rs pipeline_metrics.rs src/ && cargo run -- http://127.0.0.1:4318 ingestion
```
