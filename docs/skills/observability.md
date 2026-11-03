# Observability skills

Four skills make every service speak the same way to the same backends: logs to Loki, traces to Tempo
over OTLP, errors to Sentry or GlitchTip, pipeline metrics to Grafana. Each ships tested templates per
language, a checker, and an audit or verifier, so "wired" is proven, not claimed. The `incident`
playbook reads exactly these sources.

### service-logging

**What it is.** One JSON log format for all services in all languages, so one Loki pipeline and one set of
queries read them all. **Use it when** you create a service, add or standardise logging, replace a custom
logger, or add trace correlation. **The format.** Required on every line: `level`
(`trace|debug|info|warn|error|fatal`), `development_environment`, `service_name`, `node_name`, `logger`
(`root` or a component), `time` (UTC, exactly nine fractional digits, `Z`), `caller`
(`<project dir>/<path>:<line>`), `message`. Inside an OpenTelemetry span add `trace_id` and `span_id` together,
outside one omit both. Custom fields are flat snake_case scalars.

**What happens.** Pick the language and library (Go zerolog, Python jlogger, TypeScript pino, Rust tracing);
copy its template; configure it from the environment with the same names everywhere
(`assets/logging.env.example`); keep the existing call sites; prove the output with `scripts/logcheck.py`.
**Files.** `scripts/logcheck.py`, `assets/templates/{go,python,typescript,rust}`, `assets/log-line.schema.json`,
references `log-format`, one per language, and `migration` (moving an existing project onto the format).

### service-tracing

**What it is.** How services depend on each other, and deeper only when asked. **Two modes.** *Dependency*
(the default for any "add tracing" request): one stable identity per service, edges between services and
datastores, no internal or per-item spans. *Detailed* (only when you ask for span-level detail, business
operations, latency inside the service): custom attributes, links, log correlation, tuned sampling. The
templates make this a deploy-time switch: `TRACING_DETAIL=false` turns `detail_span()` into a no-op.

**What happens (dependency mode).** (1) Inspect startup and shutdown, HTTP/gRPC servers and clients, queue
producers and consumers, datastore clients, compose files; keep an existing provider. (2) Map the edges with
`scripts/find_dependencies.py <repo>...` (services, infrastructure, env references, Traefik routes, client
libraries and instrumentation gaps; credentials redacted) and confirm each row in code. (3) Give each service
one identity (`OTEL_SERVICE_NAME` equals `SERVICE_NAME`), the token a mounted secret. (4) Install the template
for the language and shut tracing down at exit. (5) Verify with `scripts/otlp_trace_check.py`.
**Files.** the two scripts, `assets/tracing.env.example`, templates for Go, Python, TypeScript and Rust, nine
references (dependency-map, env, per-language, lifecycle-and-export, propagation-and-spans, verification).

### service-errors

**What it is.** Unexpected errors to Sentry or GlitchTip, without leaking data. An error log line becomes
one grouped event. **The six rules.**

| # | Rule |
|---|---|
| 1 | `SENTRY_DSN` (or `SENTRY_DSN_FILE`) is the only switch; unset means nothing is sent and nothing fails; an invalid DSN fails start-up without printing it |
| 2 | only `error` and `fatal` log lines; one event per message per minute per process |
| 3 | every event carries environment (`ENV_NAME`), release (`<service_name>@<SERVICE_VERSION>`), server name (`NODE_NAME`) and tags |
| 4 | nothing private leaves: no request, user, cookies, breadcrumbs, log fields, local variables, exception text or panic payload |
| 5 | panics are captured at the HTTP recovery boundary with a fixed message and the stack |
| 6 | telemetry stays separate: SDK tracing off, a down Sentry never delays a request, flush at shutdown within 2 to 5 seconds |

**What happens.** Run `scripts/audit_errors.py <service>`; install the template for the language (Go, Python,
Rust, plus `references/frontend.md` for Next.js and Vite); add the variable and the Swarm secret
(`assets/sentry.env.example`, `compose.sentry.yaml`); verify against `scripts/sentry_receiver.py`, a local
receiver that shows what the service really sends.

### data-realtime-metrics

**What it is.** The same small metric set for every realtime pipeline, so one Grafana dashboard covers
ingestion, transform, sink and consumer services. **The idea.** One service is one pipeline; `service.name` is
`{datasource}-{role}`. Message totals only, with three statuses: `received` (every arrival, including dropped),
`dropped` (arrived, deliberately not forwarded), `published` (forwarded: Kafka ack, sink write, handled). The
only label in the whole set is `status`; never label by message type, symbol, topic or partition (per-type detail
belongs in logs); histograms and gauges carry no labels. Metrics leave over OTLP/HTTP to
`{endpoint}/v1/metrics` with an optional bearer token.

**What happens.** Pick the role (`ingestion` adds `connection_active`, `reconnects_total`, `in_flight`;
`transform`, `sink`, `consumer` add nothing); copy the template (Python, Go, TypeScript, Rust); wire the three
counters at the points a message arrives, is dropped and is forwarded; check with `scripts/otlp_check.py`; import
`assets/grafana-dashboard.json`. **References.** `metric-contract`, per-language guides, `dashboard`, `timeframes`.
