# Dagster metrics and dashboard

The names, labels, buckets and how each value is computed are the [metric contract](metric-contract.md); the schedule, sensor,
freshness and query windows are in [timeframes](timeframes.md). This page covers the dashboard and the alerts.

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
