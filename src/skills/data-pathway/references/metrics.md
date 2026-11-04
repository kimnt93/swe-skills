# Metrics for a Pathway pipeline

A Pathway job is a `transform` (or `sink`) pipeline of the [metric contract](metric-contract.md): fixed names, one `status` label, and
the clocks in [timeframes](timeframes.md). This page says where each call goes in `pipeline.py`.

| Contract call | Where in `pipeline.py` | Meaning |
|---|---|---|
| `received()` | `instrument()`: rows that pass validation and rows rejected | one per input arrival, counted once |
| `dropped()` | the rejected side of `build()` | arrived, deliberately not forwarded |
| `published(latency_ms=...)` | the cleaned table, via `pw.io.subscribe` | emitted to the Kafka writer; latency = now - event time |
| `error()` | around schema/UDF failures you survive | counted, not fatal |
| `set_backlog(fn)` | a Kafka lag probe if you have one | `stream_pipeline_consumer_lag` |

Notes

- `pw.io.subscribe(table, on_change=fn)` calls `fn(key, row, time, is_addition)`. Count only `is_addition`; a retraction is not
  a new message.
- `published` means "handed to the Kafka writer", not "acknowledged by the broker": Pathway does not surface per-message
  acks. State this when reading the dashboard; for broker acks use the Kafka client's own metrics.
- Event-to-output latency includes `autocommit_duration_ms`. A p95 close to it is the buffer, not slowness.
- Pathway also has its own monitoring (the live dashboard in a terminal and OTLP telemetry in newer versions). Use it
  for operator-level debugging; keep the shared set for the fleet-wide dashboard.

## Dashboard

`assets/grafana-dashboard.json` (uid `pathway-pipelines`): running, restarts, errors, rejected %, rows out, backlog;
rows in/rejected/out per second; event-to-output latency p50/p95/p99; input lag; last input age; output freshness; running
state timeline; errors and restarts. Import it in Grafana (Dashboards, New, Import; re-importing the uid replaces it); it filters on
the `service_name` label.

## Verify the contract

```bash
python3 scripts/otlp_check.py --role transform --wait 60 &
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318 python -m pipeline     # feed it a few messages
```

Dashboard check: `python3 ../data-dagster/scripts/check_dashboard.py assets/grafana-dashboard.json assets/template/src/pipeline/pipeline_metrics.py`
confirms every metric the dashboard queries is emitted by the template.
