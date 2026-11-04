# Dagster metrics and dashboard

Dagster has no metrics endpoint. `assets/template/src/dag/metrics.py` runs a sensor (`metrics_sensor`, every 30 s, in the
daemon) that reads the instance event log after a stored cursor and exports over OTLP/HTTP like every other service
(`OTEL_EXPORTER_OTLP_ENDPOINT`, optional bearer token; an empty endpoint makes it a no-op).

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `dagster_runs_total` | counter | `job`, `status` (`success`/`failure`/`canceled`) | finished runs |
| `dagster_run_duration_seconds` | histogram | `job` | wall time of successful runs |
| `dagster_asset_materializations_total` | counter | `asset` | materialisations recorded |
| `dagster_asset_check_failures_total` | counter | `asset` | checks that did not pass |
| `dagster_asset_last_success_timestamp_seconds` | gauge | `asset` | newest materialisation (freshness) |
| `dagster_metrics_sensor_last_tick_timestamp_seconds` | gauge | none | heartbeat of the sensor itself |

Rules: labels are job and asset names (bounded by code); never partition keys, run ids or error text. The freshness gauge is
rebuilt from the latest materialisation of every asset on each tick, so it survives a daemon restart. Counters restart from
zero with the daemon, which Prometheus `increase()` handles.

## Dashboard

`assets/grafana-dashboard.json`, uid `dagster-orchestration`: runs, failed runs, success rate, materialisations, failed
checks, stalest asset; runs per hour by status; run duration p50/p95; asset freshness table; materialisations per hour;
failures per hour; sensor heartbeat. Filters: Datasource, Service (`label_values(dagster_runs_total, service_name)`).
Import it in Grafana (Dashboards, New, Import); re-importing the uid replaces it.

Check that every queried metric is emitted:

```bash
python3 scripts/check_dashboard.py assets/grafana-dashboard.json assets/template/src/dag/metrics.py
```

## Alerts to create

- Failed runs in the last hour above 0 for a production job.
- Stalest asset above its expected period (daily asset: 30 h).
- Sensor heartbeat older than 5 minutes (the daemon is down; every other panel is stale).
- Failed blocking checks above 0.
