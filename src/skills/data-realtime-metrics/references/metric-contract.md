# Metric contract

The single metric set every realtime pipeline exports. `scripts/otlp_check.py` encodes exactly
this file; keep the two in step.

## Resource attributes (identify the pipeline)

| Attribute | Value |
|---|---|
| `service.name` | the pipeline name, `{datasource}-{role}`: `feed-ws`, `broker-mqtt` (ingestion, named after the feed), `feed-ws-transform`, `-clickhouse`, `-postgres`, `-vin-index` |
| `service.namespace` | `platform` (one value for the whole platform) |
| `deployment.environment` | `local`, `stg`, `prod` ... |
| `host.name` | the node: the host name, or the Swarm/Kubernetes node name |

Mimir/Prometheus turns `service.name` into the label `service_name`; the dashboard filters on
it. Do not add pipeline, source, stage or topic as metric labels.

## Catalog

| Metric | Type | Label | Roles | Meaning |
|---|---|---|---|---|
| `stream_pipeline_messages_total` | counter | `status` = `received` \| `dropped` \| `published` | all | see "Statuses" |
| `stream_pipeline_payload_bytes_total` | counter | - | all | bytes of the messages published |
| `stream_pipeline_latency_ms` | histogram | - | all | arrival (or Kafka timestamp) to publish acknowledgement |
| `stream_pipeline_errors_total` | counter | - | all | failures the service survived: Kafka enqueue/delivery, sink write |
| `stream_pipeline_restarts_total` | counter | - | all | process starts (1 per start) |
| `stream_pipeline_running` | gauge | - | all | 1 while the process runs, 0 at shutdown |
| `stream_pipeline_start_timestamp_seconds` | gauge | - | all | unix seconds of process start; uptime = `time() - value` |
| `stream_pipeline_kafka_healthy` | gauge | - | all | 1 while the destination (or input) topic probe succeeds |
| `stream_pipeline_last_message_age_ms` | gauge | - | all | ms since the newest live input was processed, computed at collection |
| `stream_pipeline_latest_event_timestamp_seconds` | gauge | - | all | unix seconds of the newest live input (event time if known, else receive time) |
| `stream_pipeline_consumer_lag` | gauge | - | all | backlog: Kafka lag (transform/sink/consumer) or queue depth (ingestion) |
| `stream_pipeline_connection_active` | gauge | - | ingestion | 1 while the feed connection is up |
| `stream_pipeline_reconnects_total` | counter | - | ingestion | feed reconnect attempts |
| `stream_pipeline_in_flight` | gauge | - | ingestion | messages handed to the Kafka client, not yet acknowledged |

Histogram buckets (ms): `1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000,
60000`. The upper range exists because messages wait in a buffer during a Kafka outage.

Export interval: 10 s (`OTEL_METRIC_EXPORT_INTERVAL_MS`). Temporality: cumulative (the
default of every SDK; do not switch to delta).

## Statuses

`stream_pipeline_messages_total{status}` has three values and one invariant:

```
received  =  every message that arrived, including the dropped ones
dropped   =  arrived but deliberately not forwarded          (subset of received)
published =  forwarded: acknowledged, written, or handled
received - dropped - published  =  work still in flight (>= 0)
```

What each status means per role. Dropping is optional: use it only for deliberate discards,
never for failures (failures are `errors_total`).

| Role | `received` | `dropped` | `published` |
|---|---|---|---|
| ingestion | every frame from the feed | retained/snapshot replays, heartbeat and subscription/control frames | Kafka broker acknowledgement |
| transform | records read from the input topic | records no route recognizes | records produced to the output topic |
| sink | records read from the input topic | records the store cannot accept (no event time, unknown type) | rows written / batch committed |
| consumer | messages read | messages filtered out on purpose | messages handled successfully |

Edge cases:
- A deliberate filter that discards almost everything (e.g. an aggregator that only keeps four
  symbols) is its job, not a drop: do not report `dropped` there, or the drop rate is noise.
- One input producing several outputs (a transform fanning out by type): `published` counts
  output records; `received - dropped - published` is then not zero and that is fine.
- Duplicate-collapsing sinks (upsert on a key): count the attempted write as `published`.

## How to compute each value

- **latency_ms**: record once per published message, `now - start`. `start` is when the
  service first saw it (ingestion: the receive time carried through the queue) or, for Kafka
  consumers, the record's Kafka timestamp. Include queueing and retries: it is the delay the
  data experienced inside this service, ended by the acknowledgement or committed write.
  Record `max(0, ...)` so clock skew never produces negatives.
- **payload_bytes_total**: add the output size at publish time. For raw pass-through it equals
  the input size.
- **kafka_healthy**: a background probe every 5-15 s that asks the broker for metadata of the
  topics the service needs (output for producers, input for consumers). 1 when the topics
  exist with partitions, else 0. Never hold or retry messages inside the probe.
- **consumer_lag**: Kafka: for each partition `high_watermark - 1 - last_processed_offset`
  (floor 0), summed. Keep the offsets the service has actually processed, and probe
  watermarks every 15 s. Ingestion: the length of the internal queue/channel between the feed
  reader and the Kafka writer. Non-Kafka consumers: the queue depth of their source.
- **in_flight** (ingestion): the Kafka client's own queue length (`Producer.Len()` in
  confluent-kafka-go, `len()` in confluent-kafka-python, the equivalent elsewhere). Together
  with the queue depth it separates a slow feed from a slow broker.
- **last_message_age_ms / latest_event_timestamp_seconds**: keep one atomic "newest live
  input" timestamp; compute the age inside the gauge callback so it grows between messages.
  Do not refresh it for non-live arrivals (heartbeats, retained replays): pass `live=false`.
  Emit nothing (not 0) until the first live message.
- **running / start_timestamp / restarts**: set on construction; `running` goes to 0 in the
  shutdown path before the final flush.
- **errors_total**: count each failure once at the place it is detected and survived. A failure
  that kills the process shows up as a restart instead.

## Always-on versus after-traffic

Exported from the first collection (the checker requires them): `running`, `restarts_total`,
`start_timestamp_seconds`, plus `connection_active` for ingestion. Everything else appears
once there is activity (a counter has no series until its first add; freshness gauges wait
for the first live message). Dashboards must tolerate absent series.

## Prometheus/Mimir naming rules the contract depends on

- OTLP name `stream_pipeline_messages_total` stays as is (a counter already ending in `_total`
  is not suffixed again).
- Instruments with a unit are renamed (`ms` -> `_milliseconds`, `By` -> `_bytes`): set none.
- The histogram becomes `stream_pipeline_latency_ms_bucket|_sum|_count`.
- Attributes on the resource are not metric labels, except `service.name` -> `service_name`
  (and `job`/`instance` derived by the backend).

## Transport and auth

- OTLP over HTTP, protobuf (JSON also works), to `{OTEL_EXPORTER_OTLP_ENDPOINT}/v1/metrics`.
- `Authorization: Bearer <token>` when the gateway requires it; read the token from
  `OTEL_AUTH_TOKEN` or the file named by `OTEL_AUTH_TOKEN_FILE`. Never log it.
- Probing an authenticating gateway without real data: an unauthenticated POST usually gets 401
  on every path; with a valid token, `/` gets 404 and `/v1/metrics` gets 200. A 404 on the real
  export therefore means the path was not appended.

## Extending the contract

Add a metric only when it is a service-wide aggregate that applies to a whole role. Then, in
one change: add it here, to `scripts/otlp_check.py` (`KINDS` and the role sets), to the four
templates, and to `assets/grafana-dashboard.json`. Anything per message type, symbol or topic
goes to logs (a periodic health line with per-type counts is the usual place).
