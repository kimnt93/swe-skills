# Rust (`tracing`, axum)

`account-engine` had no error tracking, so this is a **new template** that follows the layout the Rust projects share
(`tracing` for logs, config in one crate, the binary crate owns the wiring). Template:
`assets/templates/rust/errtracking.rs` (tests included, in the module), copied to the binary crate
(`svc-api/src/` in the rust-code template, `account-api/src/` in `account-engine`).

```text
<binary crate>/src/errtracking.rs     Options, init, client_options, layer, scrub, Throttle
<config crate>                        sentry_dsn (opt_secret: SENTRY_DSN or SENTRY_DSN_FILE)
<binary crate>/src/main.rs            guard = init(...); registry().with(fmt).with(errtracking::layer())
Cargo.toml.snippet                    sentry 0.49 (no default features) + sentry-tracing 0.49
```

## Wiring

1. Dependencies from `assets/templates/rust/Cargo.toml.snippet` (workspace `[workspace.dependencies]`, the binary crate,
   and `sentry` with the `test` feature as a dev-dependency).
2. Config: `sentry_dsn: String` (empty when unset) with `l.opt_secret("SENTRY_DSN")`; the loader already handles `_FILE`.
3. In `main`, before the subscriber is installed, and **keep the guard alive until the server stops**:

   ```rust
   let _errors = errtracking::init(errtracking::Options {
       dsn: Some(cfg.sentry_dsn.clone()),            // empty: off
       service_name: cfg.service_name.clone(),
       environment: cfg.env_name.clone(),
       release: format!("{}@{}", cfg.service_name, cfg.service_version),
       node_name: node_name(&cfg),
       trace_id: None,                                // see below
   });
   tracing_subscriber::registry()
       .with(filter)
       .with(tracing_subscriber::fmt::layer().json().with_current_span(false))
       .with(errtracking::layer())
       .init();
   ```

   Dropping the guard flushes for up to 2 s, so `let _errors = ...` (not `let _ = ...`, which drops at once).
4. **Trace id**: with OpenTelemetry (`account-engine`'s `telemetry` crate has a private `trace_ids()`), expose
   `pub fn current_trace_id() -> Option<String>` that reads the active span context and pass it as `trace_id:
   Some(telemetry::current_trace_id)`. It runs on the thread that logged, so it sees the right span. Without
   OpenTelemetry pass `None`.
5. Panics: the SDK's `panic` feature captures a panic as an event with its backtrace; `scrub` removes the payload text.
   Keep `panic = "unwind"` in release if you want it (the axum task catches the panic per request).

## Behaviour to keep

- Only `tracing::error!` events are forwarded (`EventFilter::Ignore` for the rest). `scrub` keeps the message and stack
  and clears request, user, breadcrumbs, contexts, extra and modules, so the event's *fields* never leave.
- Messages are constants: `tracing::error!(error = %e, order = %id, "order failed")` sends `order failed`.
- `SKIPPED` lists messages that are not failures (`request completed`); `Throttle` allows one event per message per minute.
- An unparsable DSN disables reporting instead of crashing: `client_options` never prints it, and a start-up check that
  *wants* a hard failure compares `cfg.sentry_dsn.parse::<sentry::types::Dsn>()` itself and says `SENTRY_DSN is invalid`.
- `ClientOptions` is `#[non_exhaustive]`: build it field by field (the `allow(clippy::field_reassign_with_default)` is deliberate).

## Tests (shipped)

`with_captured_events_options` runs a real subscriber with the layer and checks: one event for a repeated error, with
environment, release, server name, `service_name` and `trace_id`; nothing private (fields, user, contexts) in it; the
request summary is skipped; no, blank or invalid DSNs disable reporting. `cargo test -p <binary crate> errtracking`.
