---
name: service-errors
description: Report unexpected errors and panics from Go, Python and Rust services (and Next.js / Vite frontends) to Sentry or GlitchTip through the Sentry DSN (SENTRY_DSN, or SENTRY_DSN_FILE as a Swarm secret). Every error-level log line becomes one grouped event with the service name, environment, release and trace id, and nothing private - no request, user, breadcrumbs, local variables, exception text or log fields. Tested templates for Go, Python and Rust, with a local receiver that checks what a service really sends and a static audit. Use when adding or reviewing error tracking, Sentry, GlitchTip, panic capture or SENTRY_DSN in a service.
compatibility: Templates tested with Go 1.26 / sentry-go 0.50, Python 3.12 / sentry-sdk 2.72, Rust 1.99 / sentry 0.49. The scripts need python3 only.
metadata:
  group: observability
  summary: "Unexpected errors to Sentry or GlitchTip, with nothing private leaving"
  version: "1.0"
---

# Service errors (Sentry and GlitchTip)

One way to send unexpected errors to Sentry or the platform's GlitchTip (it speaks the Sentry protocol),
in every language, without leaking data. The service reports a failure once, with its error log line;
the SDK turns that line into one grouped event. Traces stay with OpenTelemetry
([service-tracing](../service-tracing/SKILL.md)), logs stay in Loki ([service-logging](../service-logging/SKILL.md)).

## The contract

| # | Rule | Concretely |
|---|---|---|
| 1 | **The DSN is the only switch** | `SENTRY_DSN`, or the file named by `SENTRY_DSN_FILE` (Swarm secret). Empty or unset: nothing is sent and nothing fails. An invalid DSN fails start-up **without printing it**. |
| 2 | **An error log line is the event** | `error`/`fatal` lines only; warnings, request summaries and expected faults never. One event per message per minute per process; local logs keep every line. |
| 3 | **Every event is identified** | `environment` = `ENV_NAME` (`stg`, `prod`), `release` = `<service_name>@<SERVICE_VERSION>`, server name = `NODE_NAME`, tags `service_name` and `trace_id`/`span_id` when a span is active. |
| 4 | **Nothing private leaves** | No request, user, cookies, breadcrumbs, contexts, extra data, local variables, log fields, attachments, exception text or panic payload. The detail stays in the local log line. |
| 5 | **Panics are captured at the boundary** | The HTTP recovery boundary reports a fixed message and the stack, never the panic value. |
| 6 | **Telemetry stays separate** | SDK tracing and automatic integrations are off; a down Sentry never delays a request (bounded background queue, flush at shutdown within 2-5 s). |

Details, environment and deployment: [contract](references/contract.md).

## Workflow

1. **Inspect** the service: its logger, entrypoint and shutdown, config loader, Compose files, and any existing Sentry code.
   Run the audit first: `python3 scripts/audit_errors.py path/to/service`.
2. **Install the template for the language** and follow its guide (wiring, config field, tests):

   | Language | Template | Guide |
   |---|---|---|
   | Go (zerolog, Fiber) | `assets/templates/go/errtracking.go` + `_test.go` | [go](references/go.md) |
   | Python (stdlib `logging` + unified logger) | `assets/templates/python/errors.py` + `test_errors.py` | [python](references/python.md) |
   | Rust (`tracing`) | `assets/templates/rust/errtracking.rs` (+ `Cargo.toml.snippet`) | [rust](references/rust.md) |

3. **Add the variable** to the env example and the deployment: `assets/sentry.env.example`, and
   `assets/compose.sentry.yaml` for the Swarm secret ([contract](references/contract.md#deployment)).
4. **Report once, at the place that handles the failure**: `log.Error()...Msg("static message")`. The message is the
   grouping key, so it is a constant sentence, never an interpolated id or error text.
5. **Verify** ([verification](references/verification.md)): unit tests from the template, then the local receiver:
   run the service against `SENTRY_DSN=http://test-key@127.0.0.1:9100/1`, cause one failure, stop it, then
   `python3 scripts/sentry_receiver.py check events.jsonl --environment stg --service <name>`.
6. Report what was and was not verified; a real GlitchTip project is a separate check.

## Rules that prevent the usual failures

- Never log or return the DSN: it holds the ingest key. Errors say "SENTRY_DSN is invalid", nothing more.
- Never put a user id, email, token, SQL, request body or exception text in a log message that is reported; put it in a log
  *field* (local logs only). The scrubber is the backstop, not the plan.
- Do not turn on `send_default_pii`, local variables, breadcrumbs or Sentry tracing "to see more"; open the local log by `trace_id` instead.
- A service that already has Sentry keeps its project and DSN; bring it to this contract with the audit, do not replace it blindly.
- Readable code: the templates follow the language skills' layouts; code written around them must too
  ([Go](../go-code/references/readable-code.md), [Python](../py-code/references/readable-code.md), [Rust](../rust-code/references/readable-code.md)).

## Example usage

- “Use $service-errors to add Sentry error tracking to this Go service.”
- “Use $service-errors to audit this repository and bring its error reporting to the contract.”
- “Use $service-errors to add SENTRY_DSN as a Swarm secret to this compose file.”

Frontends (Next.js, Vite + React): the same rules with the browser SDK, in [frontend](references/frontend.md).
