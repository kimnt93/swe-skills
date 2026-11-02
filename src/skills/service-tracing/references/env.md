# Tracing environment

One contract for every language. Standard OpenTelemetry variables are used where they exist; the three
`TRACING_*`/`PEER_SERVICE_*` names are this skill's. `assets/tracing.env.example` is the copyable file; the
four templates read exactly these names (`Tracing.from_env()`, `OptionsFromEnv()`, `ServiceTracing.fromEnv()`,
`Tracing::from_env()`).

## Variables

| Variable | Default | Meaning |
|---|---|---|
| `OTEL_SERVICE_NAME` (else `SERVICE_NAME`) | **required** | Stable logical service name: the node name in the dependency graph. Same value as the logger/metrics `SERVICE_NAME` and the Compose service. |
| `DEPLOYMENT_ENVIRONMENT` (else `RUN_ENV`, `ENV_NAME`) | `local` | `deployment.environment` and `deployment.environment.name` resource attributes. |
| `NODE_NAME` | hostname | `host.name`: the host, not the container id (Swarm: `"{{.Node.Hostname}}"`). |
| `SERVICE_VERSION` | none | `service.version`: an immutable revision/release. Also accepted as `service.version=` in `OTEL_RESOURCE_ATTRIBUTES`. |
| `OTEL_RESOURCE_ATTRIBUTES` | none | Extra process attributes `k=v,k=v`. Never request/user IDs. |
| `OTEL_TRACES_EXPORTER` | `otlp` | `none` disables export. |
| `OTEL_SDK_DISABLED` | `false` | `true` disables export. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | empty = no export | OTLP/HTTP **base** URL (no path); the client appends `/v1/traces`. |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | none | Trace-only endpoint; overrides the base. SDKs use it as given; the templates strip a trailing `/v1/traces` and re-append it. |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` | The templates use HTTP/protobuf; gRPC needs a different exporter and port (4317). |
| `OTEL_EXPORTER_OTLP_TIMEOUT` | `5000` | Export timeout in milliseconds. |
| `OTEL_AUTH_TOKEN` / `OTEL_AUTH_TOKEN_FILE` | none | Bearer token (**secret**, never defaulted, never committed). Swarm: mount a secret and set only the `_FILE` path. |
| `OTEL_PROPAGATORS` | `tracecontext,baggage` | W3C Trace Context + baggage. Keep every service on the same list. |
| `OTEL_TRACES_SAMPLER` | `parentbased_traceidratio` | `always_on`, `always_off`, `traceidratio`, `parentbased_*`. |
| `OTEL_TRACES_SAMPLER_ARG` | `1.0` | Ratio 0..1 for root spans. A value outside 0..1 fails at start-up. |
| `OTEL_BSP_*` | SDK defaults | Batch span processor queue/batch/delay/timeout bounds. |
| `TRACING_DETAIL` | `false` | `false` = dependency mode (boundary spans only). `true` = detailed mode: `detail_span()` records internal spans. |
| `PEER_SERVICE_<KIND>` | the kind (`postgres`, `redis`, `clickhouse`, `kafka`, `s3`) | `peer.service` for an uninstrumented dependency. Set it when the graph node should carry another name. |

Peer host and port are not tracing variables: the helpers read the deployment's infrastructure variables
(`POSTGRES_HOST`/`POSTGRES_PORT`, `REDIS_HOST`, `CLICKHOUSE_HOST`, `KAFKA_BOOTSTRAP_SERVERS`, `S3_ENDPOINT`;
see the `deployment-setup` infrastructure contract). Use the same names, or map yours in one place.

## Rules

- **Service name**: unique per deployable. Two services with one name collapse into a self edge; a name that
  changes per deployment fragments the graph. Distinct process roles deployed separately (API, worker) are
  distinct services.
- **Secrets**: the OTLP token is a bearer secret. Deliver it as a mounted secret read through
  `OTEL_AUTH_TOKEN_FILE`; do not put it in `OTEL_EXPORTER_OTLP_HEADERS` in a committed file. A header string
  needs URL-encoding (`Authorization=Bearer%20<token>`), which is why the templates build the header themselves.
- **Endpoint**: the plane's collector/gateway on the monitoring network. Never send one plane's traces to
  another plane's gateway: the gateway's plane label is authoritative.
- **Optional telemetry**: an empty endpoint must not stop the service; a collector outage must not fail requests.
- **Environment name**: the templates emit `deployment.environment` and `deployment.environment.name`; migrate
  collector/query consumers together before dropping the old one.
- **Detailed mode in production**: `TRACING_DETAIL=true` multiplies span volume. Turn it on per plane or service
  deliberately, with a sampling ratio below 1.0 on busy services.

## Compose / Swarm

Set per service (`deployment-setup` templates carry the same block):

```yaml
environment:
  OTEL_SERVICE_NAME: ${API_SERVICE_NAME:-example-api}      # == SERVICE_NAME
  OTEL_TRACES_EXPORTER: ${OTEL_TRACES_EXPORTER:-otlp}
  OTEL_EXPORTER_OTLP_ENDPOINT: ${OTEL_EXPORTER_OTLP_ENDPOINT:?OTEL_EXPORTER_OTLP_ENDPOINT is required}
  OTEL_EXPORTER_OTLP_PROTOCOL: http/protobuf
  OTEL_PROPAGATORS: tracecontext,baggage
  OTEL_TRACES_SAMPLER: ${OTEL_TRACES_SAMPLER:-parentbased_traceidratio}
  OTEL_TRACES_SAMPLER_ARG: ${OTEL_TRACES_SAMPLER_ARG:-1.0}
  TRACING_DETAIL: ${TRACING_DETAIL:-false}
  OTEL_AUTH_TOKEN_FILE: /run/secrets/otel_auth_token       # secret otel_auth_token_<plane>_v1
```

Attach the service to the monitoring network that resolves the collector and to every network its peers use.

## Example usage

- “Add the tracing environment to this compose file and `.env.example`.”
- “Why do two services show up as one node in the service graph?”
