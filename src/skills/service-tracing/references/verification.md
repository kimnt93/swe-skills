# Verify trace behavior

Use SDK in-memory exporters/test facilities and explicit test providers. Test observable behavior,
not just calls to setup. Isolate context/instrumentation without changing private SDK globals.

## Tooling

`scripts/otlp_trace_check.py` is a local OTLP/HTTP receiver (protobuf or JSON, gzip, chunked) that rebuilds the
service graph from the spans it receives, the same CLIENT→SERVER / PRODUCER→CONSUMER pairs a backend uses:

```bash
python3 scripts/otlp_trace_check.py --map docs/dependency-map.md --wait 90        # rows are the expectations
python3 scripts/otlp_trace_check.py --expect web>api --expect api>postgres --service web --wait 60
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318 <start the services>, then send one request
```

It reports services, edges (kind, count), and problems: unresolved client spans (no remote child **and** no peer
attributes: the edge would be silently dropped), self edges (shared `service.name`), `unknown_service`, missing
parents (context dropped), internal spans in dependency mode, missing `deployment.environment`. Exit 0 = every
expectation met; 1 = failed; 2 = nothing received (`--token T` checks bearer-auth wiring with a 401 otherwise).
Rows of the map with status `gap`/`inferred` are not required. To exercise a template without a service, use its
demo (`smoke.py demo`, `go test -run TestDemo` with `DEMO=1`, `npx tsx smoke.ts demo`, `cargo run -- demo`): each
prints the `traceparent` it sends downstream, so services in different languages can be chained.

## Dependency mode (default)

| Check | Evidence |
|---|---|
| Identity | Spans of each service carry its stable `service.name`; two services never share one |
| Edge continuity | For each inventoried edge, caller CLIENT/PRODUCER span and callee SERVER/CONSUMER span share a trace ID and the callee's parent is the caller's span |
| Propagation | Injected/extracted carrier preserves trace ID and sampling decision across HTTP/gRPC and message headers; a bad or missing header starts a valid new trace and does not reject the request |
| Peer identity | Client spans to uninstrumented datastores/brokers/third parties carry stable `peer.service`/`server.address` plus `db.system`/`messaging.system` |
| No extra spans | Dependency mode adds no internal or per-item spans; span count per request tracks the number of boundaries |
| Export | Spans reach the exporter after flush and bounded shutdown; collector outage follows the project's startup policy without failing requests |
| Backend graph | When access is authorized: trace a known request, confirm each service appears in one trace, and that the backend's service graph (or service-name search) shows every inventoried edge; list any missing edge |

Exercise a representative request through each inventoried synchronous hop and one producer → consumer
path, asserting parent IDs rather than trace-ID equality alone. Update the
[dependency map](dependency-map.md) statuses (`verified` / `gap`) from the evidence.

## Detailed mode

| Check | Evidence |
|---|---|
| Identity | Finished spans carry expected logical service/version/environment |
| Parentage | Shared trace ID, child parent equals upstream span ID, distinct span IDs |
| Propagation | Injected/extracted carrier preserves context and sampling decision |
| Invalid/missing context | Valid new trace; business request is not rejected solely for a bad header |
| Concurrency | Independent operations stay isolated; no stale task/log context after cleanup |
| Failure/lifetime | Safe failure events/status as appropriate; operation ends exactly once |
| Sampling | Upstream sampled/unsampled decisions and root policy behave as configured |
| Logs | Active IDs match span; outside logs omit IDs; unsampled context is understood |
| Export | Batch spans reach exporter after flush and bounded shutdown |
| Optional export/outage | Disabled/unavailable export follows policy without unexpected request failures |

Exercise representative server → client and producer → worker paths where applicable. Assert
parent IDs/links, not just trace-ID equality. Include task-failure cleanup, actual worker-process
startup when fork behavior matters, and multiple causal contexts for batch processing. Use dummy
credentials for leakage and missing-secret tests.

For local OTLP acceptance, use an isolated receiver and deterministic sampling. Check transport,
trace path, auth metadata and received spans/resources. In-memory success does not prove network
export. For an authorized backend check, locate a known operation's trace ID, confirm expected
service spans and compare logs. Account for sampling, retention and ingestion delay.

Report changed boundaries, edges verified and missing, checks passed and any untested collector/backend
path. Do not claim end-to-end tracing from successful SDK initialization or metrics export.

## Example usage

- “Verify every service edge appears in one trace and in the service graph.”
- “Verify an outgoing call is a child of the incoming server span.”
- “Test task cleanup and log correlation during concurrent processing.”
- “Diagnose why local spans exist but the collector receives no traces.”
