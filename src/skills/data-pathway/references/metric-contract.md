# Metric contract (Pathway pipelines)

The metric set every Pathway pipeline exports, so one dashboard (`assets/grafana-dashboard.json`) covers all of them.
`scripts/otlp_check.py` encodes exactly this file; `assets/template/src/pipeline/pipeline_metrics.py` implements it. Keep the three in step.

A Pathway job has one of two roles:

| Role | Shape | Example |
|---|---|---|
| `transform` | Kafka in, Kafka out | clean, window, enrich, join |
| `sink` | Kafka in, database or store out | `pw.io.postgres`, `pw.io.deltalake` |

## Resource attributes (identify the pipeline)

| Attribute | Value |
|---|---|
| `service.name` | the pipeline name, `{datasource}-{role}` (`trades-transform`, `trades-postgres`); the `SERVICE_NAME` variable, also the `service_name` of the log lines |
| `service.namespace` | `platform` |
| `deployment.environment` | `local`, `stg`, `prod` |
| `host.name` | the node |

Mimir/Prometheus turns `service.name` into the label `service_name`; the dashboard filters on it. Pipeline, topic, symbol, user and
window are **never** metric labels.

## Catalog

| Metric | Type | Label | Meaning |
|---|---|---|---|
| `stream_pipeline_messages_total` | counter | `status` = `received` \| `dropped` \| `published` | see "Statuses" |
| `stream_pipeline_payload_bytes_total` | counter | - | bytes of the rows published |
| `stream_pipeline_latency_ms` | histogram | - | event (or Kafka) time to the moment the row is handed to the output |
| `stream_pipeline_errors_total` | counter | - | failures survived: a UDF error, a sink write, a Kafka write |
| `stream_pipeline_restarts_total` | counter | - | process starts (1 per start) |
| `stream_pipeline_running` | gauge | - | 1 while the process runs, 0 at shutdown |
| `stream_pipeline_start_timestamp_seconds` | gauge | - | unix seconds of process start; uptime = `time() - value` |
| `stream_pipeline_kafka_healthy` | gauge | - | 1 while the input/output topic probe succeeds |
| `stream_pipeline_last_message_age_ms` | gauge | - | ms since the newest live input row was processed, computed at collection |
| `stream_pipeline_latest_event_timestamp_seconds` | gauge | - | unix seconds of the newest live input (event time) |
| `stream_pipeline_consumer_lag` | gauge | - | Kafka lag of the input topic(s), summed over partitions |

`stream_pipeline_connection_active`, `_reconnects_total` and `_in_flight` belong to feed-ingestion services and are not used by Pathway.

Histogram buckets (ms): `1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000, 60000`. Instruments carry no unit. Export
interval 10 s (`OTEL_METRIC_EXPORT_INTERVAL_MS`); temporality cumulative (the SDK default; never switch to delta).

## Statuses

```
received  = every input row that arrived, including the rejected ones
dropped   = arrived but deliberately not forwarded: failed validation, late beyond the allowed lateness, unroutable (subset of received)
published = forwarded: handed to the Kafka writer, or written by the sink
received - dropped - published = work still in the dataflow (>= 0), or rows that fan out / fold into windows
```

| Role | `received` | `dropped` | `published` |
|---|---|---|---|
| transform | rows read from the input topic | rows rejected by validation, rows later than the allowed lateness | rows emitted to the output table (`pw.io.subscribe` additions) |
| sink | rows read from the input topic | rows the store cannot accept (no event time, unknown type) | rows written |

- Dropping is for deliberate discards. A failure is `errors_total`, never a drop.
- A windowed aggregation folds many inputs into one output row: `published` counts output rows, so `received - dropped - published` is
  not zero and that is fine. Use the rate of `received` and of `published` separately, not their difference.
- Count only additions from `pw.io.subscribe(on_change)` (`is_addition`); a retraction is an update of a row already counted.
- `published` means handed to the Kafka writer, not acknowledged by the broker (Pathway does not surface per-message acks).

## How to compute each value

- **latency_ms**: once per published row, `max(0, now - event_time_ms)`; use the Kafka record timestamp when the payload has no event
  time. It includes `autocommit_duration_ms` (the batching delay): a p95 near that value is the buffer, not slowness.
- **payload_bytes_total**: output size at publish time.
- **kafka_healthy**: a background probe every 5-15 s that asks the broker for the metadata of the topics the job needs; 1 when they
  exist with partitions, else 0. Never block or retry rows inside the probe.
- **consumer_lag**: per partition `high_watermark - 1 - last_processed_offset` (floor 0), summed; probe watermarks every 15 s.
- **last_message_age_ms / latest_event_timestamp_seconds**: keep one "newest live input" timestamp, compute the age in the gauge
  callback so it grows between rows. Emit nothing (not 0) until the first live row.
- **running / start_timestamp / restarts**: set on construction; `running` goes to 0 on the shutdown path before the final flush.
- **errors_total**: count each failure once, where it is detected and survived. A failure that kills the process is a restart.

## Always-on versus after-traffic

Exported from the first collection (the checker requires them): `running`, `restarts_total`, `start_timestamp_seconds`. The rest appear
after traffic (a counter has no series before its first add). Dashboards tolerate absent series.

## Prometheus/Mimir naming

`stream_pipeline_messages_total` keeps its name; the histogram becomes `stream_pipeline_latency_ms_bucket|_sum|_count`; set no
instrument units (they would rename the series). Resource attributes are not labels except `service.name` -> `service_name`.

## Transport and auth

OTLP over HTTP (protobuf) to `{OTEL_EXPORTER_OTLP_ENDPOINT}/v1/metrics`; an empty endpoint turns metrics off. `Authorization: Bearer`
from `OTEL_AUTH_TOKEN` or the file named by `OTEL_AUTH_TOKEN_FILE`; never logged. A 404 on the real export means `/v1/metrics` was not appended.

## Extending the contract

Add a metric only when it is a service-wide aggregate for a whole role. In one change: this file, `scripts/otlp_check.py` (`KINDS`
and the role sets), `pipeline_metrics.py`, `assets/grafana-dashboard.json`, and `python3 ../data-dagster/scripts/check_dashboard.py` to
prove the dashboard only queries emitted metrics. Per-symbol or per-window detail goes to logs.
