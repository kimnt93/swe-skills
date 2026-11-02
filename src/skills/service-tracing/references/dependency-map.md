# Dependency map

The default tracing deliverable: a map of which services call which, and the instrumentation that
makes each edge visible. Keep it in the target project's docs next to the deployment notes.

## How trace backends build the graph

A service graph is derived from span pairs and attributes, not from configuration:

| Edge kind | Derived from | Needs |
|---|---|---|
| Sync call (HTTP/gRPC) | CLIENT span in the caller whose child is a SERVER span in the callee, same trace | Both services instrumented; context propagated in headers; distinct `service.name` per side |
| Async messaging | PRODUCER span and the CONSUMER span for the same message | Context in message headers/metadata; consumer extracts it |
| Uninstrumented target (database, cache, broker, third-party API) | CLIENT span alone with peer attributes | `peer.service` or `server.address`, plus `db.system` / `messaging.system` and destination |
| Missing edge | Context dropped, one side uninstrumented, or both sides share a service name | Fix propagation or naming |

If the backend relies on a metrics generator for the graph, an edge also needs it enabled and fresh;
discover the backend rather than assuming it.

## Discover the edges

Start with the scanner, then confirm in code:

```bash
python3 scripts/find_dependencies.py <repo> [<repo> ...]          # markdown draft, credentials redacted
python3 scripts/find_dependencies.py <repo> --json                 # for tooling
```

It reads Compose/Swarm files (service names, aliases, `*_HOST`/`*_URL` variables, infrastructure variables,
Traefik routers) and the source (HTTP/gRPC/Kafka/database/Redis/S3 clients, and whether a matching OpenTelemetry
instrumentation is present). Everything it prints is `inferred`. Then search the repository:

- **Inbound**: server/route registration, consumer groups, subscriptions, scheduled triggers.
- **Outbound HTTP/gRPC**: client constructors, base-URL/endpoint configuration keys, generated clients.
- **Messaging**: producer/consumer code, topic/queue names, header handling.
- **Datastores**: DSN/URL configuration, drivers, ORMs, object-store clients.
- **Deployment evidence**: Compose/Swarm environment variables holding peer addresses, network aliases,
  attached overlays, Traefik routers pointing at the service.
- **Third parties**: SDKs and base URLs outside the deployment.

Prefer evidence from code and configuration; mark a row `inferred` when it rests on a name only.
Do not invent edges from naming similarity. Static analysis misses dynamic discovery: confirm
inferred edges with a trace after deployment.

## Template

```markdown
| Caller | Callee | Kind | Transport / name | Context propagated | Instrumented | Evidence | Status |
|---|---|---|---|---|---|---|---|
| web | api | sync | HTTP `GET /v1/items` | traceparent header | client + server auto | `API_URL` in compose | verified |
| api | queue | async | topic `orders.created` | message header | producer + consumer | producer.go | verified |
| api | database | datastore | postgres | n/a (client span, `db.system`) | driver instrumentation | `DATABASE_URL_FILE` | verified |
| api | payments-vendor | external | HTTPS | not propagated (third party) | client span, `peer.service` | vendor client | inferred |
```

Status values: `verified` (seen in a trace/graph), `instrumented` (code done, not yet observed),
`gap` (known break, with reason and owner), `inferred`.

## Common gaps

- A proxy, gateway or sidecar strips `traceparent` or terminates the trace.
- Queue/stream clients without header support, or consumers that start new roots instead of extracting.
- Background tasks/threads that lose the active context.
- Two services sharing a `service.name` (self-edges) or a service name that changes per deployment.
- High-cardinality peer names (full URLs, IDs) fragmenting the graph into many nodes.
- Uninstrumented databases or third parties with no peer attributes (edge silently dropped).
- Services exporting to different collectors/planes, so one trace is split across backends.

## Example usage

- “Map every service this API calls and mark which edges are traced.”
- “Why is this service missing from the service graph?”
