# Timeframes (Dagster)

Six clocks meet in a scheduled pipeline. Read this before choosing a schedule delay, a freshness target, a panel window or an alert.

## 1. Partition time (the data clock)

- A **daily partition** `2026-11-03` is the data for that UTC day. It is not the time the run happened: the schedule for that
  partition runs after the day ends (the template uses `hour_of_day=1, minute_of_hour=15` and runs it at 01:15 UTC on 2026-11-04).
- Backfill = a range of partition keys; a failed day re-runs alone. Partition keys are never metric labels.
- Name the timezone of the partition definition (`timezone="UTC"`); never mix local time into partition keys.

## 2. Schedule time (the trigger clock)

- The schedule's cron (`hour_of_day`, `minute_of_hour`) and its timezone decide when a run **starts**; leave a delay after the partition ends so late source
  data has landed, and say how long late data is accepted.
- Daylight saving applies to non-UTC schedule timezones: prefer UTC.
- The daemon evaluates schedules and sensors on its own tick (about 30 s for sensors); a run starts seconds after its tick, later if the
  queued run coordinator has no free slot.

## 3. Run time (the execution clock)

- `dagster_run_duration_seconds` is `end_time - start_time` of a **successful** run, queue time excluded. Buckets run from 1 s to 2 h.
- A run that is queued behind others shows as a late materialisation, not a long duration.

## 4. Materialisation time (the freshness clock)

- `dagster_asset_last_success_timestamp_seconds` is when the newest materialisation was recorded, not the partition it covers.
- **Freshness target** per asset = schedule period + the run's normal duration + slack: a daily asset scheduled at 01:15 is
  stale after about 26 h; the template's alert uses 30 h. Write the target next to the asset.
- Age of an asset in a panel = `time() - dagster_asset_last_success_timestamp_seconds`.

## 5. Sensor and export interval (the metrics clock)

- `metrics_sensor` ticks every 30 s and the SDK exports every 10 s: a metric reaches Grafana within about a minute of the event.
  Nothing finer is visible.
- Counters are cumulative; after a daemon restart they start at 0 and `rate()`/`increase()` treat the drop as a reset. The cursor
  prevents double counting; the freshness gauge is rebuilt every tick.
- The heartbeat `dagster_metrics_sensor_last_tick_timestamp_seconds` older than 5 minutes means the daemon (or the sensor) is down and
  **every other panel is stale**.

## 6. Query windows (the dashboard clock)

| Window | Use | Meaning |
|---|---|---|
| `$__range` | totals: runs, failed runs, materialisations | total in the whole selected period |
| `$__rate_interval` | graphs: runs per hour by status | smoothing window, at least 4x the scrape interval |
| instant | stalest asset, freshness table | the latest sample within the 5 min staleness lookback |

Batch work is sparse: a daily job gives one run per day, so rate-style graphs use `increase(...[1h])` buckets and a wide time range
(24 h to 7 d). In alert rules use fixed windows; `$__rate_interval` does not exist in the ruler.

## Windows for alerts

| Question | Query shape | Window |
|---|---|---|
| A job failed? | `increase(dagster_runs_total{status="failure"}[1h]) > 0` for a production job | 1 h |
| A data check failed? | `increase(dagster_asset_check_failures_total[1h]) > 0` | 1 h |
| An asset is stale? | `time() - dagster_asset_last_success_timestamp_seconds > freshness_target` | the asset's target (daily: 30 h) |
| The daemon is down? | `time() - dagster_metrics_sensor_last_tick_timestamp_seconds > 300` | 5 min |
| Runs are slow? | p95 of `dagster_run_duration_seconds` above the job's normal range | 1 d |
| Nothing ran? | `increase(dagster_runs_total[26h]) == 0` for a daily job | 26 h |
