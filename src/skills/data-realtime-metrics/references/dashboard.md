# Pipelines dashboard

`assets/grafana-dashboard.json` is the one dashboard for every pipeline that follows
[the metric contract](metric-contract.md). It needs no per-service edits: a new pipeline
appears in the `Service` filter as soon as it exports `stream_pipeline_running`.

## Import

1. Grafana -> Dashboards -> New -> Import -> upload the JSON (uid `stream-pipelines`;
   re-importing the same uid replaces the dashboard).
2. Pick the Prometheus-compatible datasource that receives the OTLP metrics (Mimir).

Filters (the only two): **Datasource** (defaults to a datasource named `Mimir`, else the first
Prometheus-compatible one) and **Service** (`label_values(stream_pipeline_running,
service_name)`, multi-select, default All). Requirements: the backend exposes the resource
attribute `service.name` as the label `service_name`; if yours names it differently, change
the variable query and the `service_name` matchers together (search and replace in the JSON).

Defaults: time range `now/d` to `now` (today so far), refresh 10 s, UTC, shared crosshair.

## Panels and queries

`S` stands for `service_name=~"$service"`. Totals use `$__range`; graphs use `$__rate_interval`
(meaning in [timeframes.md](timeframes.md)).

| Panel | Type | Query (abridged) | Reads |
|---|---|---|---|
| Pipelines running | gauge | A `count(stream_pipeline_running{S} == 1)`; B `count(count by (service_name)(last_over_time(stream_pipeline_running{S}[$__range])))` | A is the value, B is its maximum (Config from query results transformation), so the arc is running / total |
| Total pipelines | stat | query B above | pipelines that reported in the range |
| Not running | stat | total - running | red above 0 |
| Restarts / Errors in range | stat | `sum(increase(restarts_total / errors_total{S}[$__range]))` | |
| Consumed / Produced / Dropped in range | stat | `sum(increase(messages_total{S,status="received" / "published" / "dropped"}[$__range]))` | totals over the picker range |
| Drop rate | stat | `100 * dropped / received` over the range | percent of consumed |
| Pipeline status | state timeline | `max by (service_name)(running{S})` | one row per pipeline, Down/Running |
| Consumed / Produced / Dropped messages/s | time series | `sum by (service_name)(rate(messages_total{S,status=...}[$__rate_interval]))` | per pipeline |
| Latency p95 | time series | `histogram_quantile(0.95, sum by (le, service_name)(rate(latency_ms_bucket{S}[$__rate_interval])))` | per pipeline, ms |
| Payload bytes/s | time series | `sum by (service_name)(rate(payload_bytes_total{S}[$__rate_interval]))` | |
| Backlog | time series | `max by (service_name)(consumer_lag{S})` | Kafka lag or queue depth |
| Last message age | time series | `max by (service_name)(last_message_age_ms{S})` | ms |
| Latest event age | time series | `time() - max by (service_name)(latest_event_timestamp_seconds{S})` | seconds |
| Errors/s | time series | `sum by (service_name)(rate(errors_total{S}[$__rate_interval]))` | |
| Kafka healthy | state timeline | `min by (service_name)(kafka_healthy{S})` | Unhealthy/Healthy |
| Feed connection (ingestion) | state timeline | `max by (service_name)(connection_active{S})` | ingestion only; other services have no series |
| Kafka in flight (ingestion) | time series | `max by (service_name)(in_flight{S})` | ingestion only |
| Uptime | time series | `time() - max by (service_name)(start_timestamp_seconds{S})` | seconds |
| Restarts and reconnects | time series | `sum by (service_name)(increase(restarts_total / reconnects_total{S}[$__rate_interval]))` | |

(Metric names above drop the `stream_pipeline_` prefix for width.)

Panels for ingestion-only metrics are empty for transform/sink/consumer services; that is
intended. Stat panels end in `or on() vector(0)` so a quiet range shows 0 rather than "No data".

## Extending

- **New panel**: add a target with the same `service_name=~"$service"` matcher, group
  `by (service_name)`, and use a legend of `{{service_name}}`. Keep `$__range` for totals and
  `$__rate_interval` for graphs. Check every query parses before importing: put them in a
  rules file and run `promtool check rules` (replace the Grafana variables with `.*`, `1h`
  and `5m` first).
- **New metric**: it must be in the contract first (see "Extending the contract" there).
- **Layout**: the grid is 24 columns; rows are 4/6/8 units high. Keep related panels in one row.
- **Per-environment copies**: copy the file and change `uid` and `title`; do not add an
  environment variable unless metrics from several environments share one datasource, in
  which case filter on `deployment_environment` the same way as `service_name`.

## Alert starting points

See the table at the end of [timeframes.md](timeframes.md); alert rules cannot use
`$__rate_interval` or `$service`, so use fixed windows (`5m`) and explicit matchers.
