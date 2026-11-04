# Timeframes (Pathway pipelines)

Five clocks meet in a streaming job. Most confusion comes from mixing them. Read this before choosing a window, explaining a panel or
writing an alert.

## 1. Event time, arrival time, processing time (the data clock)

| Clock | What | Where it is known |
|---|---|---|
| event time | when the thing happened (exchange or producer timestamp in the payload) | after parsing the row |
| arrival time | the Kafka record timestamp | the consumer |
| processing time | now, when Pathway handles the row | everywhere |

- **Windows use event time.** Name the column, its unit (epoch seconds in the template) and the lateness you accept.
- `latency_ms` = processing time - event time (or arrival time when the payload has none). It includes the delay of the producer,
  Kafka, and Pathway's batching; it is not a service-only number.
- `last_message_age_ms` = now - newest live input processed; `latest_event_timestamp_seconds` is that row's event time, and the
  dashboard shows `time() - value` as the latest event age. Closed markets or quiet topics make both grow without limit: that is
  normal, alert on `running`, `kafka_healthy` and lag instead.
- Keep hosts on NTP; compute with `max(0, ...)` so skew never gives negative latencies.

## 2. Window definitions (the dataflow clock)

| Window | Pathway | Meaning |
|---|---|---|
| tumbling `duration` | `pw.temporal.tumbling(duration=...)` | fixed, non-overlapping buckets; one output row per key per bucket |
| sliding `duration`, `hop` | `pw.temporal.sliding(...)` | overlapping buckets; each row counts in `duration/hop` windows |
| session `max_gap` | `pw.temporal.session(...)` | a bucket per burst of activity |

- A window's result is **updated** while rows arrive and is final only when the allowed lateness has passed; consumers of the output
  topic see updates (a retraction and a new row) unless the window is made final with a delay/cutoff. Say which the downstream expects.
- Rows later than the allowed lateness are dropped on purpose and counted as `dropped`.
- A window length is data, not a metric label: never add `1m`/`5m` to metric names or labels.

## 3. Commit interval (the engine clock)

`autocommit_duration_ms` is how often Pathway commits a minibatch to the output. It adds up to that much latency to every row and is the
lower bound of freshness. Pick it from the freshness the consumer needs (100-1000 ms is typical); a latency p95 close to it is the buffer.

## 4. Export interval (the service clock)

- The SDK exports every `OTEL_METRIC_EXPORT_INTERVAL_MS` (default **10 s**); nothing finer is visible on a dashboard.
- Counters are cumulative; the backend derives rates. After a restart the counter restarts at 0 and `rate()`/`increase()` treat it as a
  reset. The first sample of a series has nothing to subtract from, so ignore it in `increase()`.
- Gauges are sampled at collection time; `last_message_age_ms` is computed then.
- On shutdown the job flushes once more (`running = 0`); without it the last interval is lost.

## 5. Query windows (the dashboard clock)

| Window | Use | Meaning |
|---|---|---|
| `$__range` | `increase(x[$__range])` totals | total in the whole selected period |
| `$__rate_interval` | `rate()`/`increase()` in graphs | smoothing window, at least 4x the scrape interval (about 1 min) |
| instant | "running now", gauges | the latest sample within the 5 min staleness lookback |

- A rate is an average over `$__rate_interval`, not an instantaneous value.
- After a pipeline stops, its series vanish from instant queries about 5 minutes later, so `running == 0` / `absent()` alerts lag ~5 min.
- p95 latency is `histogram_quantile(0.95, sum by (le)(rate(stream_pipeline_latency_ms_bucket[$__rate_interval])))`, estimated from
  buckets (resolution is the bucket width).
- In alert rules use a fixed window (`5m`); `$__rate_interval` is a Grafana variable and does not exist in the ruler.

## Windows for alerts

| Question | Query shape | Window |
|---|---|---|
| Down? | `max by (service_name)(stream_pipeline_running) == 0` or `absent_over_time(...[5m])` | 5 min or more |
| Stuck? | `rate(stream_pipeline_messages_total{status="received"}[5m]) == 0` while the topic should have traffic | 5-10 min |
| Kafka? | `min(stream_pipeline_kafka_healthy) == 0` | 1-2 min |
| Behind? | `stream_pipeline_consumer_lag` rising and not recovering | 10-15 min |
| Slow? | p95 latency above target (minus the commit interval) | 10 min |
| Crash looping? | `increase(stream_pipeline_restarts_total[15m]) > 3` | 15 min |
| Rejecting too much? | `increase(dropped[15m]) / increase(received[15m]) > threshold` | 15 min |
