---
name: data-realtime-metrics
description: Add OpenTelemetry (OTLP) metrics to realtime stream pipelines and consumer services - feed ingestion, Kafka transforms, sinks, consumers - in Python, Go, TypeScript/JavaScript or Rust, using one shared metric set (stream_pipeline_*) so every pipeline appears on one Grafana dashboard. Use when starting or instrumenting a streaming pipeline, ingestion service, Kafka consumer or sink, when asked for OTel, OTLP, Prometheus or Mimir metrics (throughput, latency, lag, drops, health, restarts) for such a service, or when importing or extending the pipelines dashboard.
compatibility: Needs an OTLP/HTTP metrics endpoint (collector or gateway). The checker script needs python3 only. Templates tested with Python 3.12 / opentelemetry-sdk 1.38, Go 1.26 / otel-go 1.47, Node 22 / sdk-metrics 2.12, Rust 1.99 / opentelemetry 0.33.
metadata:
  group: observability
  summary: "The same OTel metric set for every realtime pipeline, one Grafana dashboard"
  version: "1.0"
---

# Pipeline OTel metrics

Every realtime pipeline exports the same small metric set, so one dashboard covers ingestion,
transform, sink and consumer services in any language. The contract is fixed; your job is to
wire it into the service, not to design metrics.

## The idea in five lines

- One service = one pipeline. `service.name` (the `SERVICE_NAME` variable, also the `service_name` of the `service-logging` skill's log lines) is the pipeline name (`feed-ws`, `broker-mqtt`,
  `feed-ws-transform`): `{datasource}-{role}`. Dashboards filter by it.
- Message totals only, three statuses: `received` (every arrival, including dropped),
  `dropped` (arrived but deliberately not forwarded), `published` (forwarded: Kafka ack, sink
  write, handled). The only label in the whole set is `status`.
- Never label by message type, symbol, topic, partition or exchange timeframe (1m, 1H...).
  Per-type detail belongs in logs.
- Histograms and gauges carry no labels and no unit.
- Metrics leave over OTLP/HTTP to `{endpoint}/v1/metrics` with an optional bearer token.

## Steps

1. **Pick the role** and service name. Ask the user only if it is not obvious from the code.

   | Role | Shape | Extra metrics |
   |---|---|---|
   | `ingestion` | feed (websocket, MQTT, HTTP) -> Kafka | `connection_active`, `reconnects_total`, `in_flight` |
   | `transform` | Kafka -> Kafka | none |
   | `sink` | Kafka -> database or store | none |
   | `consumer` | Kafka or queue -> application logic | none |

2. **Copy the template** for the language into the service and read its guide:

   | Language | Template (copy this) | Guide (read this) |
   |---|---|---|
   | Python | `assets/templates/python/pipeline_metrics.py` | [references/python.md](references/python.md) |
   | Go | `assets/templates/go/metrics.go` | [references/go.md](references/go.md) |
   | TypeScript / JavaScript | `assets/templates/typescript/pipelineMetrics.ts` | [references/typescript.md](references/typescript.md) |
   | Rust | `assets/templates/rust/pipeline_metrics.rs` | [references/rust.md](references/rust.md) |

   The four templates expose the same methods: `received`, `dropped`, `published`, `error`,
   `reconnect`, `set_connected`, `set_kafka_healthy`, `set_backlog`, `set_in_flight`,
   `shutdown`. Construction counts the restart and marks the pipeline running. Use the
   template as is; change names only to match local style.

3. **Wire the calls** at the right places (details and per-role meaning in
   [references/metric-contract.md](references/metric-contract.md)):
   - input loop / message handler: `received` for every arrival; `dropped` for each message
     you skip on purpose (retained replays, control frames, unroutable or undated rows).
   - after the output succeeds (broker ack, committed write): `published(bytes, latency)`.
     Latency runs from arrival (or the Kafka timestamp) to this point.
   - failures you survive (enqueue/delivery/write errors): `error`.
   - a background probe every 5-15 s of the destination topic: `set_kafka_healthy`.
   - backlog: `set_backlog` returns Kafka lag (consumers) or in-memory queue depth (ingestion).
   - ingestion only: `set_connected` on connect/disconnect, `reconnect` per retry,
     `set_in_flight` with the Kafka client's queue length.
   - process start and shutdown: construct once; call `shutdown` on exit so the last export is
     flushed and `running` reports 0.

4. **Configure through the environment**, same names in every language (see
   [assets/otel.env.example](assets/otel.env.example)): `OTEL_EXPORTER_OTLP_ENDPOINT`,
   `OTEL_AUTH_TOKEN` (or `OTEL_AUTH_TOKEN_FILE` for Swarm/Kubernetes secrets),
   `OTEL_METRIC_EXPORT_INTERVAL_MS` (default 10000), `SERVICE_NAME`,
   `DEPLOYMENT_ENVIRONMENT`, optional `NODE_NAME` (default: the host name). An empty endpoint
   must disable export without breaking the service.

5. **Verify with the checker before finishing.** It is a local OTLP receiver that fails on any
   contract violation (wrong names, labels, units, missing resource attributes, missing
   always-on metrics):

   ```bash
   python3 scripts/otlp_check.py --role transform --wait 30 &
   OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318 <start the service, send a few messages>
   ```

   Each template folder also has a smoke test that exercises every method (see its guide).
   A connection error from the service's very last flush after the checker already printed
   its verdict is harmless. `warn` lines for metrics that appear only after traffic mean the
   run was too quiet; send messages and re-run.

6. **Dashboard.** Import [assets/grafana-dashboard.json](assets/grafana-dashboard.json) once
   per Grafana; every pipeline that follows the contract shows up in its `Service` filter
   without edits. Read [references/dashboard.md](references/dashboard.md) to extend it or to
   build alerts, and [references/timeframes.md](references/timeframes.md) before explaining
   or choosing any time window (export interval, rate window, "in range" totals, latency
   start/end points, event time versus receive time).

## Gotchas

- **Readable code.** The templates here follow the language skills' readable layout (one statement per line, 100 columns for Go and Rust, 79 for Python,
  small functions, no crammed one-liners). Code you add to them or write around them must too: [Go](../go-code/references/readable-code.md),
  [Python](../py-code/references/readable-code.md), [Rust](../rust-code/references/readable-code.md); TypeScript follows the same rules with Prettier.
- **No unit on `stream_pipeline_latency_ms`.** A unit (`ms`) makes Mimir/Prometheus rename the
  series to `..._ms_milliseconds_bucket` and the p95 panel goes empty. Same for byte counters.
- **Append `/v1/metrics` yourself.** Several OTLP/HTTP clients use a configured URL as given
  (Go since otel-go 1.43, JS `url`, Rust `with_endpoint`); a gateway answers 404 for `/`.
- **`dropped` is also `received`.** Count every arrival as `received`, then `dropped` for the
  skipped ones; the dashboard's drop rate is `dropped / received`.
- **Counters are cumulative.** A restart resets them to 0; `rate`/`increase` handle that. Do
  not persist counters across restarts and do not try to "fix" the first sample.
- **One meter provider per process,** created once. In Python use the provider's own meter,
  not the global one, so tests can build several.
- **Flush on shutdown** or the last interval of data (and `running=0`) is lost.
- **Idle feeds look broken.** `last_message_age_ms` grows when a market is closed; do not
  alert on it without a schedule.
- **Do not invent metrics.** If something is missing from the contract, add it to the
  contract file, the checker, the templates and the dashboard together, in every service.

## Files

- [references/metric-contract.md](references/metric-contract.md) - full catalog, statuses, per-role meaning, how to compute each value.
- [references/timeframes.md](references/timeframes.md) - what every time window and timestamp means.
- [references/dashboard.md](references/dashboard.md) - panels, queries, extending, alerts.
- `references/python.md`, `go.md`, `typescript.md`, `rust.md` - language guides.
- `assets/` - dashboard JSON, env template, one tested template per language.
- `scripts/otlp_check.py` - the conformance checker.
