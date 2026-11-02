# Propagation and spans

Propagation applies to both modes; the span-design and log-correlation sections below are **detailed
mode** (add them only when requested; dependency mode keeps boundary spans from libraries).

Use SDK W3C Trace Context injection/extraction. Preserve `traceparent`, `tracestate` and sampling
choices; missing/invalid context starts an independent operation under SDK policy. Avoid handcrafted
headers/fixed IDs. Context is correlation, not authorization. Allow-list baggage and keep secrets
and personal data out of it. See [context propagation](https://opentelemetry.io/docs/concepts/context-propagation/).

| Boundary | Guidance |
|---|---|
| HTTP/gRPC server | Extract context and start a server span through supported middleware |
| Outgoing call | Client span plus context injection; avoid duplicate automatic/manual spans |
| Queue producer | Inject producer context into supported message headers/metadata |
| Task/consumer | Extract message context and scope processing span to the work |
| Async/thread/process | Capture/restore context where the runtime does not carry it |
| Retry/persisted task | Define causal parentage or linked traces for separate attempts |

Choose messaging parents/links according to installed semantic conventions and application
lifecycle. Batches can have multiple causal contexts: use links instead of arbitrarily selecting
one parent. Long-delayed jobs may use linked traces; preserve an intentional persisted-context
contract without imposing one lifetime trace per entity.

Detach/reset context on every task exit to prevent leakage. Automatic consumer instrumentation
and manual business spans should have distinct responsibilities, not conflicting roots. Use
headers/metadata when supported; do not change payload schemas without a contract need.

## Design spans (detailed mode)

Name spans by stable operation or route template, not raw URLs, IDs, symbols or payloads. Select
SERVER, CLIENT, PRODUCER, CONSUMER or INTERNAL according to the actual operation. Prefer existing
protocol/database instrumentation and manual spans for meaningful business work.

Use safe attributes and the project's semantic-convention version. Avoid credential/header dumps,
raw bodies and SQL text; exception messages can leak sensitive data too. Record failure events
and error status as appropriate: recording an exception does not necessarily set status. Follow
protocol conventions for expected responses. End spans after actual operation completion,
including async acknowledgments when they define completion.

High-throughput streams need bounded operation/batch spans and sampling, rather than an infinite
loop span or unlimited per-message spans. Metrics remain the throughput/lag signal.

## Correlate logs (detailed mode)

Get IDs from active valid span context, not a request ID or independently generated pair. Inside
logs match the active span; outside logs omit both IDs. Unsampled valid context may have no stored
trace. Clean up bound logger/async-local state after work and verify simultaneous operations
remain isolated. Response trace headers are a project contract choice, not an OTel requirement.
