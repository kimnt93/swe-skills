# Rust (tracing)

Template: `assets/templates/rust/service_logging.rs` (add as a module). Smoke binary: `main.rs`;
dependencies and the `otel` feature: `Cargo.toml` (same folder). Tested with Rust 1.99, `tracing`
0.1, `tracing-subscriber` 0.3, `tracing-opentelemetry` 0.34 with `opentelemetry` 0.33.

```toml
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["registry", "fmt", "std", "env-filter"] }
serde_json = { version = "1", features = ["preserve_order"] }
time = { version = "0.3", features = ["formatting", "macros"] }
gethostname = "1"
# trace ids: opentelemetry = "0.33", tracing-opentelemetry = "0.34"  (the template's `otel` feature)
```

## Use

```rust
mod service_logging;

service_logging::init_from_env("ssi-data")?;          // SERVICE_NAME, DEVELOPMENT_ENVIRONMENT|ENV_NAME, NODE_NAME, LOG_LEVEL;
                                                      // "ssi-data" = project directory name in `caller`
tracing::info!(messages_received = 361234u64, channel_depth = 0u64, "message statistics");
tracing::warn!(target: "api.request", request_id = %rid, duration_ms = 1250.5, "slow request");
tracing::error!(error = %err, error_type = "SinkError", table = "trades", "sink write failed");
tracing::error!(fatal = true, "cannot continue");    // level "fatal"
```

Trace ids: compose the layer with your tracer instead of `init`:

```rust
let otel = tracing_opentelemetry::layer().with_tracer(provider.tracer("my-service"));
tracing_subscriber::registry().with(otel).with(service_logging::layer(service_logging::options_from_env("ssi-data")?)).init();
```

Events inside an entered `tracing` span (or an attached OpenTelemetry context) then carry
`trace_id`/`span_id`. Without the `otel` feature the fields are never written.

Docker: set `NODE_NAME` (Swarm `{{.Node.Hostname}}`); the template falls back to the hostname.

## What the template does

- a `FormatEvent` writes one JSON line to stdout with the unified fields; `logger` is the event
  target (the module path, or `target: "api.request"`);
- `time` is UTC with nine digits (`[subsecond digits:9]`);
- `caller` is `<root>/<file>:<line>` from the event metadata (`file!()` relative to the workspace);
  paths of dependencies are cut at the cargo registry;
- level `fatal` comes from an `error!` event with `fatal = true` (tracing has no fatal level);
- custom fields keep their JSON type; a name colliding with a core field becomes `field_<name>`.

## Gotchas

- Use `%err` (Display) for the `error` field; `?err` writes the Debug form.
- The level filter is an `EnvFilter` built from `LOG_LEVEL`; a library crate must not call
  `init`, only the binary does (the data-engine Python binding installs its own only when no host
  subscriber exists).
- To keep third-party crates quiet (they may log endpoints), use a `Targets` filter for your own
  crates instead of the plain level.
- Never put secrets in fields: `tracing` records whatever you pass.

## Verify

```bash
cp -r assets/templates/rust /tmp/log-smoke && cd /tmp/log-smoke && mkdir src && mv main.rs service_logging.rs src/
SERVICE_NAME=ssi-ws-v3 ENV_NAME=local NODE_NAME=docker-host-1 LOG_LEVEL=debug cargo run -q --features otel \
  | python3 <skill>/scripts/logcheck.py --service ssi-ws-v3 --env local --node docker-host-1 --require-trace
```
