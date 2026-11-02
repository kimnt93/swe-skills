# Existing projects versus the unified format

Surveyed in October 2026 across the platform's projects. All of them already agree on the core
idea (`development_environment`, `service_name`, `node_name`, `time`, `caller`, `level`,
`message`, flat custom fields); they differ in details that break one shared query or parser.
This skill does not change those projects; use the table when you migrate one.

| Project | Stack | Differences from the unified format |
|---|---|---|
| `ssi-data`, `dnse-data` | Go, zerolog, stdout | `time` uses `RFC3339Nano`, which trims trailing zeros (not fixed 9 digits); error key is `exception`; no `logger`; no `trace_id`/`span_id`; `NODE_NAME` default `local` |
| `trading-simulator` | Go, zerolog, stdout | `time` is `RFC3339` (seconds); no `node_name`; no `logger`; `caller` is zerolog's default (full path unless built with `-trimpath`); trace ids only in the request middleware, added by hand |
| `data-stream` | Python, jlogger, stdout | `time` from jlogger's `RFC3339` option is local time with microseconds and **no zone** (`2026-10-07T10:32:24.171474`); no `caller`; levels `warning`/`critical`; `NODE_NAME` default `local`; no trace ids |
| `data-engine` | Rust `tracing` + Python jlogger, stderr | `time` has seconds only; no `logger`; Python emits `warning`/`critical` while Rust emits `warn`; no trace ids; logs to stderr (right for a library) |
| `alpha-server` | Python stdlib bridged to jlogger, stderr | `time` has milliseconds; levels `warning`/`critical`; `trace_id`/`span_id` are empty strings outside a span; errors as `error.type`, `error.message`, `error.stack`; extra core fields `service_version`, `component`, `process` (fine as optional fields) |

## Migration, per stack

- **Go (zerolog)**: replace the logger setup with `assets/templates/go/logger.go`
  (`ConfigureFromEnv`). Changes: fixed-width time layout, `ErrorFieldName = "error"`,
  `logger` field via `Named`, trace hook (`.Ctx(ctx)` on events), caller relative to the module.
  Search the repo and dashboards for the `exception` key.
- **Python (jlogger)**: replace the module with `assets/templates/python/service_logging.py`
  (`configure_from_env`). It supplies `time`, `caller` and level names that jlogger does not,
  keeps the fluent jlogger encoder, and bridges stdlib `logging`. Replace
  `with_error(...)` call sites with `log.exception(...)` or `log.error(msg, exc)`.
  A project that already has a stdlib handler (alpha-server) keeps its context binding
  (request ids) and swaps only the field rules: UTC nanosecond `time`, `warn`/`fatal`, omitted
  empty trace ids, flat `error`/`error_type`/`stack`.
- **Rust (tracing)**: replace the custom `FormatEvent` with
  `assets/templates/rust/service_logging.rs` (adds `logger`, 9-digit time, relative caller,
  `fatal`, trace ids). Keep the target filter that stops third-party crates from logging.
- **TypeScript/JavaScript**: new services start from `assets/templates/typescript/serviceLogging.ts`.

## After migrating

1. `SERVICE_NAME`, `DEVELOPMENT_ENVIRONMENT`/`ENV_NAME` and `NODE_NAME` come from the
   environment (Swarm: `NODE_NAME: "{{.Node.Hostname}}"`); `SERVICE_NAME` equals the metrics `service.name`.
2. Run the service and pipe its output through `scripts/logcheck.py --service ... --env ... --node ...`.
3. Update the Loki queries that used `level="warning"`, `exception`, or `error.type`.
4. Add a unit test that captures a line and asserts the required fields (the smoke test of the
   template is a starting point).
