# Metric contract (Dagster)

The metric set every Dagster code location exports, so one dashboard (`assets/grafana-dashboard.json`, uid `dagster-orchestration`)
covers all of them. `assets/template/src/dag/metrics.py` implements it and `assets/template/tests/test_metrics.py` asserts it;
`scripts/check_dashboard.py` proves the dashboard queries only metrics the code emits. Keep the four in step.

Dagster has no metrics endpoint. The daemon runs `metrics_sensor` (every 30 s); it reads the instance event log after a stored cursor
and exports over OTLP/HTTP like every other service.

## Resource attributes (identify the deployment)

| Attribute | Value |
|---|---|
| `service.name` | the code location, `{team}-dagster` (`SERVICE_NAME`, default `dagster`); also the `service_name` of the log lines |
| `service.namespace` | `platform` |
| `deployment.environment` | `local`, `stg`, `prod` (`ENV_NAME`) |
| `host.name` | the daemon's host |

Mimir/Prometheus turns `service.name` into `service_name`; the dashboard filters on it.

## Catalog

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `dagster_runs_total` | counter | `job`, `status` = `success` \| `failure` \| `canceled` | finished runs |
| `dagster_run_duration_seconds` | histogram | `job` | wall time of successful runs |
| `dagster_asset_materializations_total` | counter | `asset` | materialisations recorded |
| `dagster_asset_check_failures_total` | counter | `asset` | checks that did not pass |
| `dagster_asset_last_success_timestamp_seconds` | gauge | `asset` | unix seconds of the newest materialisation (freshness) |
| `dagster_metrics_sensor_last_tick_timestamp_seconds` | gauge | none | heartbeat of the sensor itself |

Histogram buckets (s): `1, 5, 15, 30, 60, 120, 300, 600, 1800, 3600, 7200`. Instruments carry no unit. Export interval 10 s,
temporality cumulative (the SDK default; never switch to delta).

## Label rules

- Labels are **job and asset names**, which the code bounds. Never partition keys (a new value per day), run ids, error text, user
  names or paths: each would create a series per value.
- `status` has exactly three values. A run that never finishes has no status yet; the heartbeat and the stalest asset show it.
- One label set per metric, as above; do not add `partition`, `repository`, `location` or `tag` labels.

## How each value is computed

- **runs_total / duration**: one record per `RUN_SUCCESS`, `RUN_FAILURE`, `RUN_CANCELED` event after the cursor. Duration is
  `end_time - start_time` of the run record, success only, `max(0, ...)`.
- **materializations_total**: one per `ASSET_MATERIALIZATION` event. A multi-asset or a retried partition counts each materialisation.
- **check_failures_total**: one per `ASSET_CHECK_EVALUATION` with `passed == false`. A passing check is not counted.
- **asset_last_success_timestamp_seconds**: rebuilt from the latest materialisation of **every** asset on each tick
  (`get_latest_materialization_events`), so it survives a daemon restart and covers assets that did not run recently.
- **sensor_last_tick**: set at the start of each tick; if the daemon stops, it stops moving.
- The **cursor** is the highest event storage id handled; it is stored in the sensor's cursor, so a tick never counts an event twice.

## Always-on versus after-activity

The heartbeat and the freshness gauges appear from the first tick; counters appear after the first run, materialisation or failed check.
Dashboards tolerate absent series. Counters restart from zero with the daemon; `increase()` handles the reset.

## Transport and auth

OTLP over HTTP to `{OTEL_EXPORTER_OTLP_ENDPOINT}/v1/metrics`; an empty endpoint makes the sensor skip (a no-op). Optional bearer token
from `OTEL_AUTH_TOKEN(_FILE)`; never logged.

## Extending the contract

Add a metric only when it is an aggregate over jobs or assets. In one change: this file, `metrics.py`, `test_metrics.py`, the
dashboard, and run `scripts/check_dashboard.py`. Per-partition and per-run detail belongs in Dagster's UI and in logs.
