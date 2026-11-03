# Python

Template: `assets/templates/python/pipeline_metrics.py` (copy it into the service). Smoke test:
`assets/templates/python/smoke.py`.

Tested with Python 3.12 and `opentelemetry-sdk` / `opentelemetry-exporter-otlp-proto-http`
1.38 (the template uses `explicit_bucket_boundaries_advisory`, so keep the SDK recent).

```bash
uv add opentelemetry-sdk opentelemetry-exporter-otlp-proto-http   # or pip install
```

## Wire it

```python
import os
from pipeline_metrics import PipelineMetrics

token = open(os.environ["OTEL_AUTH_TOKEN_FILE"]).read().strip() if os.getenv("OTEL_AUTH_TOKEN_FILE") else os.getenv("OTEL_AUTH_TOKEN", "")
metrics = PipelineMetrics(
    os.environ["SERVICE_NAME"],                      # e.g. feed-ws-transform
    environment=os.getenv("DEPLOYMENT_ENVIRONMENT", "local"),
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", ""),
    token=token,
    export_interval_ms=int(os.getenv("OTEL_METRIC_EXPORT_INTERVAL_MS", "10000")),
    ingestion=False,                                 # True for feed -> Kafka services
)
try:
    run()                                            # your loop
finally:
    metrics.shutdown()                               # flush + running=0
```

Kafka consumer loop (confluent-kafka):

```python
msg = consumer.poll(1.0)
if msg is None or msg.error():
    continue
_, ts_ms = msg.timestamp()                           # Kafka timestamp, ms
metrics.received(event_ms=ts_ms)
if not route(msg):                                   # deliberate discard
    metrics.dropped()
    continue
write(msg)                                           # your output; raises on failure
metrics.published(bytes=len(msg.value()), latency_ms=time.time() * 1000 - ts_ms)
```

Producer delivery callback (ingestion or transform output); bind the arrival time to it:

```python
import functools, time

def delivered(started: float, err, msg):               # runs inside producer.poll()/flush()
    if err:
        metrics.error()
    else:
        metrics.published(bytes=len(msg.value()), latency_ms=(time.time() - started) * 1000)

producer.produce(topic, value, on_delivery=functools.partial(delivered, time.time()))
```

Background probe (thread, every 5-15 s) for `set_kafka_healthy`, `set_backlog`:

```python
md = consumer.list_topics(topic, timeout=5)           # healthy if the topic has partitions
lag = sum(max(0, consumer.get_watermark_offsets(TopicPartition(topic, p), timeout=5)[1] - 1 - processed.get(p, -1)) for p in md.topics[topic].partitions)
metrics.set_backlog(lambda: lag)
metrics.set_in_flight(lambda: len(producer))         # ingestion only
```

## Gotchas

- Keep the `PipelineMetrics` instance global to the process; the exporter thread is a daemon
  thread owned by the SDK.
- Do not call `opentelemetry.metrics.set_meter_provider` yourself: the template uses its own
  provider's meter (the global setter works once per process and tests need several).
- The HTTP exporter is blocking and uses `requests`; `shutdown()` can wait for its timeout if
  the gateway is down. Do not call it from an async event loop thread without an executor.
- The recording methods are safe to call from any thread (OTel instruments are thread-safe; the
  template guards its own freshness state with a lock).
- Frameworks that process in batches (Pathway, Spark-like): count per batch with
  `received(count=n)` / `published(count=n)`, not per row in Python.

## Verify

```bash
python3 scripts/otlp_check.py --role ingestion --wait 30 &
cd assets/templates/python && python smoke.py http://127.0.0.1:4318 ingestion
```
