# Timeframes: what every window and timestamp means

Read this before explaining a panel, choosing a query window, or writing an alert. Four
different clocks are involved; most confusion comes from mixing them.

## 1. Export interval (the service clock)

- The SDK collects and exports every `OTEL_METRIC_EXPORT_INTERVAL_MS` (default **10 s**).
  Nothing in a dashboard is finer than that: a 1 s spike is invisible.
- Counters are **cumulative**: each export carries the total since process start. The backend
  derives rates from differences. After a restart the counter restarts at 0; `rate()` and
  `increase()` treat the drop as a reset.
- The first sample of a new series has nothing to subtract from, so `increase()` over a window
  that contains only the first export under-reports by that first value. Ignore it.
- Gauges are sampled at collection time. `last_message_age_ms` is computed then, so it grows
  between messages and drops to ~0 when a message arrives.
- On shutdown the service flushes once more (`running=0`). Without that flush the last
  interval is lost.

## 2. Query windows (the dashboard clock)

| Window | Where it comes from | Use it for | Meaning |
|---|---|---|---|
| `$__range` | the time picker (e.g. "Today so far", "Last 6 hours") | "in range" totals: `increase(metric[$__range])` | total messages/errors/restarts in the whole selected period |
| `$__rate_interval` | Grafana: at least 4x the datasource's configured scrape interval (default 15 s, so about 1 min) | `rate()` and `increase()` inside graphs | smoothing window per point; follows the zoom level but never goes below that floor |
| instant (no window) | the latest sample within 5 min lookback | "running now", gauges | current state |
| `last_over_time(x[$__range])` | whole picker range | "pipelines seen in range" | the last value each series reported in the range, so a pipeline that has since stopped is still counted |

Consequences:
- **Rate per second** (`rate`) is an average over `$__rate_interval`, not an instantaneous
  value. Messages/s of 120 means "120 per second averaged over about a minute".
- **"in range"** panels are `increase` over the picker range: pick "Last 15 minutes" and the
  Consumed stat is the last 15 minutes; pick "Today" and it is since midnight (the dashboard
  default `now/d`). The stat's sparkline shows how that running total built up.
- **Pipelines running (now / total)**: `now` = series whose latest sample is within the 5 min
  lookback and equals 1; `total` = distinct `service_name` that reported anywhere in the
  range. A pipeline that crashed 10 minutes ago drops out of "now" but stays in "total", so
  the gauge falls below 100%.
- **Staleness**: after a service stops sending, its series vanish from instant queries about 5
  minutes later. Alerts on `absent()` or on `running == 0` therefore fire with a ~5 min lag.
- **p95 latency** is `histogram_quantile(0.95, sum by (le)(rate(bucket[$__rate_interval])))`:
  the 95th percentile of the messages published during that window, estimated from bucket
  counts (resolution is the bucket width; the worst bucket edge is 60 s).

## 3. Latency, ages and event times (the data clock)

Three timestamps can describe the same message:

| Clock | What | Where it is known |
|---|---|---|
| event time | when the market event happened (exchange timestamp in the payload) | only after parsing the payload |
| ingestion/receive time | when the first service received it | ingestion service; Kafka record timestamp downstream |
| processing time | now, when this service handles it | everywhere |

How the contract uses them:
- `latency_ms` = **processing time - (receive time or Kafka timestamp)**, ended at the
  acknowledgement. It measures delay inside our system, not exchange-to-us delay. Ingestion
  starts the clock at receive; transforms/sinks start at the Kafka record timestamp of the
  newest input in the batch.
- `last_message_age_ms` = now - newest live input processed. Healthy realtime feeds sit
  below a few seconds during trading hours.
- `latest_event_timestamp_seconds` is an absolute time; the dashboard shows
  `time() - value` as "latest event age". Ingestion services do not parse payloads, so for
  them it is receive time; a service that does know the event time may report that instead.
  Document which one a service uses in its METRICS file.
- Closed markets: all ages and "latest event age" grow without limit after the session
  ends, and consumed/produced rates drop to zero. That is normal; alert with a trading
  schedule or on `kafka_healthy`, `running` and `connection_active` instead.
- Clock skew: ages and latencies are computed on the service host. Use `max(0, ...)` and keep
  hosts on NTP.

## 4. Data timeframes are not metric dimensions

Bars such as `1m`, `1H`, `1D` (OHLCV timeframes) are data fields. Never add them as a metric
label, stage or name suffix. A pipeline that emits all three counts them together in
`published`; if per-timeframe counts matter, put them in the periodic health log line.

## Choosing windows for alerts

| Question | Query shape | Window guidance |
|---|---|---|
| Is the pipeline down? | `max by (service_name)(stream_pipeline_running) == 0` or `absent_over_time(...[5m])` | at least 5 min (staleness) |
| Is it stuck? | `rate(stream_pipeline_messages_total{status="received"}[5m]) == 0` while `connection_active == 1` | 5-10 min, only inside trading hours |
| Is Kafka the problem? | `min(stream_pipeline_kafka_healthy) == 0` for 1-2 min; rising `in_flight` and `consumer_lag` | 1-5 min |
| Is it falling behind? | `consumer_lag` increasing over 10 min and not recovering | 10-15 min |
| Is it slow? | p95 latency above target for 10 min | `$__rate_interval` is fine; use `5m` in alert rules |
| Crash looping? | `increase(stream_pipeline_restarts_total[15m]) > 3` | 15 min |
| Dropping too much? | `increase(dropped[15m]) / increase(received[15m]) > threshold` | 15 min; thresholds depend on the feed (ingestion drops heartbeats by design) |

In alert rules replace `$__rate_interval` with a fixed window (`5m`); it is a Grafana
variable and does not exist in the ruler.
