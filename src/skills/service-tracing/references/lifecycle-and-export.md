# Lifecycle and export

## Provider ownership

Initialize tracing at the process entrypoint before instrumented work. Libraries consume tracing
APIs/context; applications own provider configuration and shutdown. Use one active provider owner
per process, idempotent setup and no duplicate instrumentation. Preserve an existing lifecycle
abstraction rather than adding another global provider.

Prefork workers need process-local exporters initialized through supported child hooks; inherited
threads/connections may not survive forking. Python's global provider is normally set once. Use
explicit test providers or an existing lifecycle abstraction; do not overwrite private SDK globals
or introduce a reloadable provider unless the project actually needs it.

Batch export off the request path, bound queues and timeouts, and preserve the project's required
or optional telemetry startup policy. Collector outages must not unexpectedly break requests.
Stop accepting work, finish operations, then flush/shut down within the process grace period.
Abrupt termination may lose buffered spans.

## Identity

Discover service name/version, environment and instance/host identity sources. Align logical names
with logs/metrics; preserve intentional process-role distinctions. Do not put request/user IDs in
resources or substitute container identity for a documented host label.

The current environment resource attribute is `deployment.environment.name`; existing integrations
may use `deployment.environment`. Preserve compatibility intentionally and migrate collector/query
consumers together. See the [deployment resource convention](https://opentelemetry.io/docs/specs/semconv/resource/deployment-environment/).

## OTLP configuration

Discover transport, receiver, TLS and authorization from the target deployment. gRPC and HTTP
exporters are not interchangeable. HTTP uses the trace signal path; gRPC uses its service method.
Standard generic endpoint configuration is a base URL; a trace-specific endpoint is used as given.
Explicit SDK constructors can differ: verify the installed exporter to avoid omitted/doubled paths.
See the [OTLP exporter specification](https://opentelemetry.io/docs/specs/otel/protocol/exporter/).

Check which standard `OTEL_EXPORTER_OTLP_*` or project-specific variables are consumed and their
precedence. Custom SDK setup may not honor disable/exporter/sampler environment variables. A
working metrics endpoint does not prove a trace receiver exists.

Auth headers are secrets. Use approved runtime delivery; `_FILE` handling is an app/wrapper
convention, not universal exporter support. Configure the correct HTTP headers or gRPC metadata,
without logging values or embedding them in images. Use supported parsing and the endpoint's TLS
policy; do not disable certificate verification to repair connectivity.

## Sampling

Dependency mode keeps the default parent-based policy so each inbound request's decision is honored
through all hops; tune sampling further only in detailed mode or when volume demands it. Use an
explicit traffic-appropriate policy: parent-based sampling with a configurable root ratio preserves
upstream decisions. Validate the ratio and the treatment of external context. Do not force sampled
flags or generate synthetic sampled parents to bypass root sampling.

Head sampling cannot guarantee retaining later failures. Tail sampling cannot recover spans
already dropped in the application; align policies before promising all errors are retained.
See [sampling](https://opentelemetry.io/docs/concepts/sampling/).
