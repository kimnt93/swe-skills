# Unified log format

One JSON object per line. Every service, in every language, writes the same
shape, so one Loki pipeline and one set of queries read all of them. `scripts/logcheck.py`
and `assets/log-line.schema.json` encode exactly this file.

```json
{"level":"info","development_environment":"local","service_name":"ssi-ws-v3","node_name":"docker-host-1","logger":"root","messages_received":361234,"messages_enqueued":361234,"messages_published":361233,"kafka_errors":0,"channel_depth":0,"time":"2026-10-07T02:49:55.245633769Z","caller":"ssi-data/cmd/ssi-data/main.go:171","message":"message statistics"}
```

Inside an OpenTelemetry span the same line also carries `"trace_id":"4bf92f3577b34da6a3ce929d0e0e4736","span_id":"00f067aa0ba902b7"`.

## Fields

Required on every line:

| Field | Value |
|---|---|
| `level` | `trace`, `debug`, `info`, `warn`, `error`, `fatal` (lowercase, exactly these) |
| `development_environment` | from `DEVELOPMENT_ENVIRONMENT`, else `ENV_NAME`, else `local` |
| `service_name` | from `SERVICE_NAME`; the pipeline/service name, identical to the OTel `service.name` of the metrics skill (`ssi-ws-v3`, `ssi-ws-v3-transform`) |
| `node_name` | from `NODE_NAME`: the Docker/Kubernetes **host** (see below); fallback: the hostname |
| `logger` | `root` for the process's default logger, or a module/component name (`api.request`, `kafka.producer`). In Rust it defaults to the module path (the `tracing` target) |
| `time` | UTC RFC 3339 with **exactly 9** fractional digits and `Z`: `2026-10-07T02:49:55.245633769Z`. Pad with zeros when the clock is coarser. Go's `RFC3339Nano` trims zeros and is not allowed |
| `caller` | `<root>/<path relative to the project root>:<line>`: `ssi-data/cmd/ssi-data/main.go:171`. Always relative, always with a line number, never an absolute or `..` path. `<root>` is the project directory name |
| `message` | short, lowercase, no trailing period: `message statistics`, `sink write failed` |

Optional, standard names (use them when they apply):

| Field | Value |
|---|---|
| `trace_id`, `span_id` | OpenTelemetry ids, 32 and 16 lowercase hex characters. Present **together** when the event is inside a valid span; **omitted** otherwise (never empty strings, never all zeros) |
| `error` | the error message string |
| `error_type` | the error class/type name (`ZeroDivisionError`, `SinkError`, `*errors.errorString`) |
| `stack` | stack trace of an exception, only on `error`/`fatal`, at most 8000 characters |
| `service_version`, `component` | optional identity extras (`component`: `api`, `worker`, `cli`) |

Everything else is a **custom field**: flat, snake_case, scalar values (string, number, bool).
Good names: `duration_ms`, `rows`, `status_code`, `request_id`, `messages_received`,
`channel_depth`. A custom field may not reuse a core name: the templates write it as
`field_<name>` (so `time=5` becomes `field_time`). Long strings are truncated at 2000
characters; non-finite numbers and unknown objects become strings.

Order is not part of the contract (parsers ignore it). The Go output follows zerolog's natural
order: level, identity, logger, custom fields, trace ids, time, caller, message.

## Environment variables (same in every language)

| Variable | Meaning | Default |
|---|---|---|
| `SERVICE_NAME` | `service_name` | **required** (startup fails without it) |
| `DEVELOPMENT_ENVIRONMENT` | `development_environment`; `ENV_NAME` is the accepted alternative, `DEVELOPMENT_ENVIRONMENT` wins when both are set | `local` |
| `NODE_NAME` | `node_name` | the hostname |
| `LOG_LEVEL` | minimum level; `warning` and `critical` are accepted aliases of `warn` and `fatal` | `info` |
| `LOG_CALLER` | TypeScript only: `false` drops `caller` where capturing a stack per line is too costly | `true` |

### NODE_NAME is the Docker host

`node_name` answers "which machine did this run on". Inside a container the hostname is the
container id, which is useless for that, so the platform injects the host:

| Runtime | How `NODE_NAME` reaches the process |
|---|---|
| Docker Swarm | `NODE_NAME: "{{.Node.Hostname}}"` in the service `environment` (a Swarm service template, resolved per task) |
| Compose, `network_mode: host` | leave it unset: the container shares the host's hostname |
| Compose, bridge network | `NODE_NAME=$(hostname) docker compose up` with `NODE_NAME: ${NODE_NAME}` in the file, or a line in `.env` |
| `docker run` | `-e NODE_NAME=$(hostname)` |
| Kubernetes | `env: [{name: NODE_NAME, valueFrom: {fieldRef: {fieldPath: spec.nodeName}}}]` |

A bridge-network container with `NODE_NAME` unset logs its container id; that is the
signal that the variable was forgotten.

## Rules

- **Output**: services write to **stdout** (the container runtime collects it); libraries and
  CLI tools that also print results write logs to **stderr**. Never write plain text to the
  same stream: `logcheck.py` ignores non-JSON lines, but collectors will not.
- **Levels**: `debug` internals and waits; `info` lifecycle (start, stop, connected, periodic
  statistics); `warn` recoverable problems (retry, dropped records, reconnect); `error` a
  failure the caller or operator must know about; `fatal` the process is about to exit.
  Map library levels exactly: warning -> `warn`, critical -> `fatal`. Go's `Fatal()` exits;
  prefer returning an error and logging `error`.
- **Log once per operation**, not per message in a hot path: load complete, connect,
  reconnect/backoff, batch written. Per-message detail belongs in metrics. A periodic
  statistics line (every 30-60 s) with the counters is the usual bridge between the two.
- **Errors**: `error` = message, `error_type` = class, `stack` only for unexpected
  exceptions. The legacy names `exception` and `error.type`/`error.stack` are not used.
- **Trace correlation**: pass the request/message context so the span ids are attached
  (Go: `.Ctx(ctx)` on the event; Python/TypeScript/Rust: automatic inside an active span). Do
  not invent ids; no span means no fields. `trace_id` is the join key between a log line,
  its trace and (via `service_name`) the service's metrics.
- **Never log** credentials, tokens, DSNs or URLs with credentials, SQL text, full message
  payloads or personal data. Name the variable instead (`DATABASE_URL is not set`).
  `logcheck.py` warns on credential-looking keys and values.
- **Timestamps** come from the wall clock at emit time and never feed business logic.

## Level mapping across libraries

| Unified | Go zerolog | Python stdlib / jlogger | Rust tracing | TypeScript pino |
|---|---|---|---|---|
| `trace` | trace | (debug) | TRACE | trace |
| `debug` | debug | DEBUG / debug | DEBUG | debug |
| `info` | info | INFO / info | INFO | info |
| `warn` | warn | WARNING / `warning` -> mapped | WARN | warn |
| `error` | error | ERROR / error | ERROR | error |
| `fatal` | fatal | CRITICAL / `critical` -> mapped | `fatal = true` field on an error event | fatal |

## Loki

Promote only `development_environment`, `service_name` and `node_name` to labels (low
cardinality). `caller`, `logger`, `trace_id`, `level` and custom fields stay parsed fields.

```logql
{service_name="ssi-ws-v3"} | json | level="error"
{service_name=~"ssi-ws-v3.*", development_environment="prod"} | json | logger="kafka.producer"
{service_name="ssi-ws-v3"} | json | trace_id="4bf92f3577b34da6a3ce929d0e0e4736"
```

Starting point for a Grafana Alloy pipeline (not tested here): `loki.process` with
`stage.json` extracting `time`, `level`, `service_name`, `development_environment`,
`node_name`; `stage.labels` for the three identity fields; `stage.timestamp` with
`source = "time"` and `format = "RFC3339Nano"`.

## Verify

```bash
<service> 2>&1 | python3 scripts/logcheck.py --service ssi-ws-v3 --env local --node docker-host-1
```

`--require-trace` additionally demands at least one line with trace ids. The same rules as a
JSON Schema are in `assets/log-line.schema.json` (for other validators and pipelines).
