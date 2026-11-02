---
name: service-tracing
description: Add or review OpenTelemetry tracing in Go, Python, TypeScript/JavaScript or Rust services. Default mode traces service dependencies only - one stable service name per service plus boundary spans and W3C context propagation so the service graph (who calls whom over HTTP/gRPC, queues and datastores) is complete and verified. Detailed mode (internal spans, attributes, span links, log correlation, sampling tuning) only when the user asks for it. Includes tested templates, the tracing environment contract, a dependency scanner and a local OTLP verifier.
compatibility: Templates tested with Go 1.26 / otel-go 1.47, Python 3.13 / opentelemetry-sdk 1.45, Node 22 / sdk-trace-node 2.12, Rust / opentelemetry 0.33. The scripts need python3 only (the scanner reads Compose files with PyYAML when installed).
metadata:
  group: observability
  version: "2.0"
---

# Service tracing

Trace how services depend on each other, and go deeper only when asked. Keep concrete service names,
endpoints and infrastructure settings in the target project.

## Choose the mode

| Mode | When | Result |
|---|---|---|
| **Dependency** (default) | Any tracing request that does not ask for more: "add tracing", "trace this service", "show service dependencies / the service graph" | One stable identity per service; every call between services, queues and datastores is a boundary span with propagated context; a documented, verified dependency map |
| **Detailed** | The user asks for span-level detail: "detailed tracing", "trace business operations", "where does latency go inside the service", custom attributes, links, log correlation, tuned sampling | Dependency mode **plus** internal spans, safe attributes, links for batches/retries, trace/log correlation |

Start in dependency mode and say so. Switch only on request, or when the goal cannot be met otherwise (state
why). Never add internal or per-item spans "for completeness" in dependency mode. The templates enforce this:
`TRACING_DETAIL=false` (default) makes `detail_span()` a no-op, so detailed mode is a deploy-time switch.

## Workflow (dependency mode)

1. **Inspect.** Read project instructions, startup/shutdown code, dependency versions, telemetry setup, HTTP/gRPC
   servers and clients, queue producers/consumers, datastore clients and the Compose/Swarm files. Preserve an
   existing provider, logger and instrumentation; distinguish tracing from metrics-only SDK setup.
2. **Map the edges.** Draft the map from evidence:
   `python3 scripts/find_dependencies.py <repo> [<repo>...]` lists services, infrastructure and service-to-service
   env references, Traefik routes, client libraries and **instrumentation gaps** (credentials are redacted).
   Confirm each row in code, then keep it in the project's docs ([dependency map](references/dependency-map.md)).
3. **Give each service one identity** and the shared environment: copy the variables from
   `assets/tracing.env.example` ([environment contract](references/env.md)). `OTEL_SERVICE_NAME` equals
   `SERVICE_NAME` of logs/metrics and the Compose service; the token is a mounted secret, never a default.
4. **Install the template for the language** and its guide; build one tracing handle at the entrypoint and shut it down:

   | Language | Template | Guide |
   |---|---|---|
   | Go | `assets/templates/go/tracing.go` | [go](references/go.md) |
   | Python | `assets/templates/python/service_tracing.py` | [python](references/python.md) |
   | TypeScript / JavaScript | `assets/templates/typescript/serviceTracing.ts` | [typescript](references/typescript.md) |
   | Rust | `assets/templates/rust/service_tracing.rs` | [rust](references/rust.md) |

   The four templates expose the same helpers: `server_span`, `client_span`, `peer_span`, `producer_span`,
   `consumer_span`, `detail_span`, `inject`/`ids`, `shutdown`. They read the environment contract, parse W3C
   context safely (missing or invalid context starts a new trace), honour parent-based sampling, record error
   types only and export in batches with a bounded flush.
5. **Instrument boundaries only.** Prefer the framework/driver instrumentation named in the language guide for
   inbound requests, outbound clients, messaging and datastores; use the helpers for hops no library covers.
   Every hop must propagate context ([propagation](references/propagation-and-spans.md)); an uninstrumented
   datastore, broker or third party gets `peer_span` so the graph shows a named node instead of dropping the edge.
6. **Keep it cheap.** No internal spans, no per-message spans on high-throughput feeds (propagate headers, sample),
   parent-based sampling, export off the request path. Metrics remain the throughput signal.
7. **Wire the deployment.** Compose/Swarm environment, secret and network for the collector come from the
   `deployment-setup` templates (same names); this workflow also works without that skill.
8. **Verify** ([verification](references/verification.md)): run the receiver, drive one request through the
   services, and require every mapped edge: `python3 scripts/otlp_trace_check.py --map docs/dependency-map.md`.
   Update the map's status column (`verified` / `gap`).

## Detailed mode (on request)

Everything above, plus: manual spans for significant application work with stable names and correct kinds,
closed on every path; links for batches and separately executed retries; safe semantic-convention attributes;
an explicit sampling policy ([lifecycle and export](references/lifecycle-and-export.md)); and trace/log
correlation (`trace_id` + `span_id` together, omitted when invalid; `service-logging` supplies the JSON
contract when available). Set `TRACING_DETAIL=true` for the chosen service/plane and verify with
`otlp_trace_check.py --mode detailed`.

## Rules that prevent the usual failures

- One `service.name` per deployable; two services sharing one collapse into a self edge.
- Provider ownership: one per process, created at the entrypoint (per worker after fork); never install a
  second provider, logger or context manager.
- Never put secrets, payloads, SQL text or high-cardinality values in span names, attributes or status.
- A missing collector must not stop the service or fail requests; an empty endpoint disables export.
- SDK initialization or a metrics export does not prove tracing: only received spans and observed edges do.
- **Readable code.** The templates here follow the language skills' readable layout (one statement per line, 100 columns for Go and Rust, 79 for Python,
  small functions, no crammed one-liners). Code you add to them or write around them must too: [Go](../go-code/references/readable-code.md),
  [Python](../py-code/references/readable-code.md), [Rust](../rust-code/references/readable-code.md); TypeScript follows the same rules with Prettier.

## Verify the skill's own pieces

`python3 scripts/otlp_trace_check.py` is the same receiver the templates were tested against: Go → Node →
Python → Rust services passing `traceparent` produced the five expected edges (including datastore peer edges).

## Example usage

- “Use $service-tracing to add tracing to this service so it appears in the service graph.” (dependency mode)
- “Use $service-tracing to map and trace dependencies between these services and verify every edge.”
- “Use $service-tracing in detailed mode to trace the order flow inside this service and its workers.”
- “Use $service-tracing to add the tracing environment to this compose file.”
