---
name: service-logging
description: Set up unified structured JSON logging for services in Go (zerolog), Python (kimnt93/jlogger), TypeScript/JavaScript (pino) or Rust (tracing). Every line has level, development_environment, service_name, node_name, logger, an RFC 3339 nanosecond UTC time, caller as file:line, and optional OpenTelemetry trace_id and span_id, with identity read from SERVICE_NAME, DEVELOPMENT_ENVIRONMENT/ENV_NAME and NODE_NAME. Use when creating a service, adding or standardizing logging, replacing a custom logger, adding trace correlation to logs, or checking that log output matches the platform format and Loki labels.
compatibility: The checker script needs python3 only. Templates tested with Go 1.26 / zerolog 1.35, Python 3.12 / jlogger 0.1, Node 22 / pino 10, Rust 1.99 / tracing 0.1.
metadata:
  group: observability
  summary: "One JSON log format in Go, Python, TypeScript and Rust, checked by logcheck"
  version: "1.0"
---

# Service logging

One log format for every service, in every language, so one Loki pipeline and one
set of queries read all of them. The format is fixed; your job is to wire the template into
the service and prove the output with the checker.

```json
{"level":"info","development_environment":"local","service_name":"feed-ws","node_name":"docker-host-1","logger":"root","messages_received":361234,"channel_depth":0,"time":"2026-10-07T02:49:55.245633769Z","caller":"feed-data/cmd/feed-data/main.go:171","message":"message statistics"}
```

Required on every line: `level` (`trace|debug|info|warn|error|fatal`), `development_environment`,
`service_name`, `node_name`, `logger` (`root` or a component name), `time` (UTC, exactly 9
fractional digits, `Z`), `caller` (`<project dir>/<relative path>:<line>`), `message`. Inside an
OpenTelemetry span add `trace_id` and `span_id` together; outside one omit both. Custom fields are
flat snake_case scalars. Full spec: [references/log-format.md](references/log-format.md).

## Steps

1. **Pick the language** and copy the template into the service; read its guide:

   | Language | Library | Template (copy this) | Guide (read this) |
   |---|---|---|---|
   | Go | zerolog | `assets/templates/go/logger.go` | [references/go.md](references/go.md) |
   | Python | kimnt93/jlogger | `assets/templates/python/service_logging.py` | [references/python.md](references/python.md) |
   | TypeScript / JavaScript | pino | `assets/templates/typescript/serviceLogging.ts` | [references/typescript.md](references/typescript.md) |
   | Rust | tracing | `assets/templates/rust/service_logging.rs` | [references/rust.md](references/rust.md) |

   Use the library named in the table: the existing services already use zerolog and
   jlogger. Do not add a second logging library next to it. If the service already has a logger,
   replace its setup with the template and keep its call sites; [references/migration.md](references/migration.md)
   lists what usually differs and how to migrate.

2. **Configure from the environment**, same names everywhere (template:
   [assets/logging.env.example](assets/logging.env.example)):

   | Variable | Becomes | Default |
   |---|---|---|
   | `SERVICE_NAME` | `service_name` | required: fail at startup without it |
   | `DEVELOPMENT_ENVIRONMENT` (or `ENV_NAME`) | `development_environment` | `local` |
   | `NODE_NAME` | `node_name` | the hostname |
   | `LOG_LEVEL` | minimum level | `info` |

   `NODE_NAME` must be the Docker **host**, not the container id. Swarm: `NODE_NAME:
   "{{.Node.Hostname}}"`; Compose with `network_mode: host`: leave it unset; Compose bridge:
   `NODE_NAME=$(hostname)`; Kubernetes: `spec.nodeName` through the downward API. `SERVICE_NAME`
   is the same value as the OpenTelemetry `service.name` of the metrics (see the
   `data-realtime-metrics` skill), so logs, metrics and traces join on it.

3. **Call the setup once at process start** (`ConfigureFromEnv`, `configure_from_env`,
   `configureFromEnv`, `init_from_env`), before any other code logs. Services write to
   **stdout**, one JSON object per line; libraries and CLIs that also print results write logs
   to stderr. Replace `print`, `console.log`, `fmt.Println` diagnostics.

4. **Log with the rules** (details in [references/log-format.md](references/log-format.md)):
   - `info` for lifecycle and a periodic statistics line, `warn` for recoverable problems,
     `error` for failures, `fatal` only just before exiting; `debug` for internals.
   - Log once per operation, never per message in a hot path; counters belong in metrics.
   - Errors: `error` (message), `error_type`, and `stack` only for unexpected exceptions.
   - Pass the request/message context so `trace_id`/`span_id` are attached (Go needs
     `.Ctx(ctx)` on the event; Python, TypeScript and Rust pick the active span up themselves).
   - Never log credentials, tokens, DSNs, SQL text or message payloads.

5. **Verify before finishing.** Run the service (or the template's smoke test), pipe its output
   through the checker, and read every FAIL:

   ```bash
   <service> 2>&1 | python3 scripts/logcheck.py --service <SERVICE_NAME> --env <env> --node <node> --require-trace
   ```

   `--require-trace` only when the code runs inside spans. Exit code 0 means every line conforms
   (required fields, 9-digit UTC time, relative caller with a line number, level names, trace ids
   all-or-nothing and non-zero, no duplicate keys). Warnings flag non-snake_case or nested
   fields and credential-looking keys or values. Add a unit test that captures one line and
   asserts the required fields.

6. **Loki.** Promote only `development_environment`, `service_name` and `node_name` to labels;
   everything else stays a parsed field (see the Loki section of the format reference).

## Gotchas

- **Readable code.** The templates here follow the language skills' readable layout (one statement per line, 100 columns for Go and Rust, 79 for Python,
  small functions, no crammed one-liners). Code you add to them or write around them must too: [Go](../go-code/references/readable-code.md),
  [Python](../py-code/references/readable-code.md), [Rust](../rust-code/references/readable-code.md); TypeScript follows the same rules with Prettier.
- **`time` has exactly 9 fractional digits.** Go's `RFC3339Nano` trims trailing zeros; the
  template uses a fixed layout. JavaScript and Python derive the nanoseconds explicitly.
- **jlogger alone is not enough**: its RFC3339 option has no timezone, there is no `caller`, and
  it writes `warning`/`critical`. The Python template fixes all three and keeps jlogger's encoder.
- **`caller` must be relative** and carry the project directory name. Build Go binaries with
  `-trimpath` (the template also handles non-trimpath builds started inside the module).
- **Empty trace ids are a bug.** Omit both fields when there is no active span.
- **A custom field named like a core field** (`time`, `level`, `logger`, ...) is renamed
  `field_<name>` by the templates; the checker flags duplicate keys from other loggers.
- **Container hostname is the container id.** A bridge-network container with `NODE_NAME` unset
  logs its container id: set the variable.
- **Do not mix plain text into the stream**; collectors parse JSON only.

## Files

- [references/log-format.md](references/log-format.md) - the spec: fields, env, levels, rules, Loki.
- [references/migration.md](references/migration.md) - what usually differs in an existing logger and how to migrate.
- `references/go.md`, `python.md`, `typescript.md`, `rust.md` - language guides.
- `assets/` - one tested template per language, JSON Schema, env template.
- `scripts/logcheck.py` - the conformance checker.
