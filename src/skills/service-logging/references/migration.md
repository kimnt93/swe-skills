# Migrating an existing logger

Most services already log JSON with the core idea of the unified format (`development_environment`,
`service_name`, `node_name`, `time`, `caller`, `level`, `message`, flat custom fields). They differ in details
that break one shared query or parser. Typical differences to look for:

| Difference | Seen as | Fix |
|---|---|---|
| `time` layout | `RFC3339Nano` trims trailing zeros; `RFC3339` has seconds only; a local time with no zone | fixed UTC time, exactly 9 fractional digits, `Z` |
| level names | `warning` and `critical` instead of `warn` and `fatal` | map to the unified names |
| missing identity | no `node_name`, no `logger`, a default of `local` | read from the environment; `logger` is `root` or a component name |
| `caller` | zerolog's full path, or none | `<project dir>/<relative path>:<line>` |
| error fields | `exception`, `error.type`, `error.message`, `error.stack` | flat `error`, `error_type`, `stack` |
| trace ids | missing, or empty strings outside a span | `trace_id` and `span_id` together inside a span, both omitted outside |

## Migration, per stack

- **Go (zerolog)**: replace the logger setup with `assets/templates/go/logger.go`
  (`ConfigureFromEnv`). Changes: fixed-width time layout, `ErrorFieldName = "error"`,
  `logger` field via `Named`, trace hook (`.Ctx(ctx)` on events), caller relative to the module.
  Search the repo and dashboards for the `exception` key.
- **Python (jlogger)**: replace the module with `assets/templates/python/service_logging.py`
  (`configure_from_env`). It supplies `time`, `caller` and level names that jlogger does not,
  keeps the fluent jlogger encoder, and bridges stdlib `logging`. Replace
  `with_error(...)` call sites with `log.exception(...)` or `log.error(msg, exc)`.
  A project that already has a stdlib handler keeps its context binding
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
