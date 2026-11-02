# Error-tracking contract

## What is sent, what is not

| Sent (an event) | Never sent |
|---|---|
| the **static log message** (the grouping key) | log fields (`error`, ids, payload sizes), exception text, a panic's payload |
| the **stack** of the failure (file, function, line; no source variables) | request URL, headers, body, cookies, query string |
| `environment`, `release`, server name | user id, email, IP address, username |
| tags `service_name`, `component`, `logger`, `trace_id`, `span_id` | breadcrumbs, contexts, extra data, modules, attachments |

Why so strict: a Sentry project is read by more people than the production logs, and an exception text or a frame's
locals routinely hold a connection string, a token or submitted data. Everything needed to debug is one search away:
copy the event's `trace_id` into Tempo and Loki, where the full, access-controlled detail lives. Opting in to exception
text is a conscious per-service choice (`include_exception_text=True` in Python); the Go and Rust templates have no such switch.

## Environment

| Variable | Meaning | Default |
|---|---|---|
| `SENTRY_DSN` | project DSN `http://<key>@glitchtip.common.@DOMAIN@/<project id>`; blank = off | unset |
| `SENTRY_DSN_FILE` | file holding the DSN (Swarm secret); read when `SENTRY_DSN` is unset | unset |
| `ENV_NAME` | the event `environment` (`stg`, `prod`, `local`); same resolution order as the log format | `local` |
| `SERVICE_NAME` | tag `service_name` and the release prefix | required by the service |
| `SERVICE_VERSION` | release suffix: the image tag or digest | `""` |
| `NODE_NAME` | the event server name | hostname |

The DSN is read in the config layer only (the same place as every other secret), kept as a secret type, and compared
against nothing. An invalid DSN is a start-up error that says `SENTRY_DSN is invalid` and never echoes the value.

## Projects and environments

- **One GlitchTip/Sentry project per service**, named after `SERVICE_NAME` (for example `platform/order-api`).
  Both planes (stg, prod) may share it: they are told apart by `environment`, so filter on it instead of creating a
  project per plane. Create the project and note its numeric id before the first release.
- The platform's GlitchTip is at `glitchtip.common.@DOMAIN@`. Inside a plane overlay the host is an alias of
  Traefik, so an `http://` DSN works from the container. Use the DSN the project page shows, unchanged.
- GlitchTip accepts the Sentry **envelope and store** endpoints but not every newer SDK feature: keep SDK tracing,
  profiling and metrics off, and (Go) the JSON envelope transport (`DisableTelemetryBuffer: true`).

## What becomes an event

| Becomes an event | Does not |
|---|---|
| an `error` or `fatal` log line (a failed task, a 5xx, an unrecoverable dependency error) | warnings, expected faults (a simulated 429, a retry, a reconnect) |
| a panic at the HTTP recovery boundary (fixed message + stack) | the per-request summary line (`request completed`) |
| an unhandled exception that reaches the process boundary | an error already reported by the line that handled it |

Report **once**: a failure is logged at the place that handles it, and the log line is the event. Do not log and
re-log the same error in each layer, and do not call `capture_exception` yourself next to a log line.

**Throttle**: one event per message per minute per process. A tight retry loop produces one event and a counter in
the metrics, not thousands of events. The local logs keep every occurrence.

## Deployment

- Swarm: the DSN is an external secret `{service}_sentry_dsn_{env}_v1` mounted at `/run/secrets/{service}_sentry_dsn`,
  with `SENTRY_DSN_FILE` pointing at it: [assets/compose.sentry.yaml](../assets/compose.sentry.yaml).
  (`alpha-server` keeps the DSN as plain plane configuration in `deploy/<plane>.env` because an ingest key can only
  write events; a service that follows the secret convention, like `trading-simulator`, is the default here.)
- Local: leave `SENTRY_DSN` empty. To see events, run `scripts/sentry_receiver.py` and point the DSN at it.
- Every container of the service gets it (api, workers, matchers). Give each process role `component` so events can be
  split (`api`, `worker`, `matcher`). A one-shot child that handles untrusted code (a sandbox) gets **no** DSN.
- `deployment-setup`'s `check_deploy.py` does not know this secret; the audit does: `scripts/audit_errors.py`.

## Rules

1. The log message passed to the reported line is a constant sentence. Variable parts go in log fields.
2. Do not include the DSN in a log, a health `config`, an error body or a test snapshot.
3. A reporting failure (network, bad DSN at runtime) is swallowed; it never raises into the request path.
4. Shutdown flushes with a bounded wait (2-5 s) and then closes the client; do not block the exit on Sentry.
5. Tests prove the privacy rules with a fake receiver (each template ships them); they must keep passing when the
   SDK is upgraded, because defaults change between SDK versions.
