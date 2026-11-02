# Python

Template: `assets/templates/python/service_tracing.py` (copy into the service). Tests and demo:
`assets/templates/python/smoke.py`. Tested with Python 3.13 and `opentelemetry-sdk` /
`opentelemetry-exporter-otlp-proto-http` 1.45.

```bash
uv add opentelemetry-sdk opentelemetry-exporter-otlp-proto-http      # or pip install
```

## Wire it

```python
from service_tracing import Tracing

tracing = Tracing.from_env()        # OTEL_SERVICE_NAME|SERVICE_NAME, RUN_ENV, OTEL_* (references/env.md)
try:
    run()
finally:
    tracing.shutdown()              # flush within the exporter timeout
```

Create it once per process at the entrypoint, before instrumented libraries are used. The global provider is
set once; tests build `Tracing(Options(...), exporter, set_global=False, processor=SimpleSpanProcessor(exporter))`
and never touch private SDK state. Prefork servers (gunicorn/uvicorn workers, Celery prefork) need one
`Tracing` **per worker process**, created in the post-fork hook (`post_fork`, `worker_process_init`).

## Boundary spans (dependency mode)

| Hop | Use |
|---|---|
| Litestar/ASGI inbound | `litestar.plugins.opentelemetry.OpenTelemetryInstrumentationMiddleware` (needs `opentelemetry-instrumentation-asgi`; outermost middleware, then rename the span to `scope["path_template"]`), or `tracing.server_span(route, request.headers)` |
| Outbound HTTP | `instrumentation-httpx` / `-requests` / `-aiohttp-client`, or `with tracing.client_span("GET /pricing", peer="pricing") as headers:` and pass `headers` |
| PostgreSQL | `instrumentation-psycopg` / `-psycopg2` / `-asyncpg` / `-sqlalchemy`; otherwise `tracing.peer_span("postgres", "select orders")` |
| Redis | `instrumentation-redis`; otherwise `peer_span("redis", "get")` |
| ClickHouse, S3/RustFS | `peer_span("clickhouse", "insert trades")`, `peer_span("s3", "put object")` (`instrumentation-botocore` covers boto3) |
| Kafka (`confluent-kafka`) | `with tracing.producer_span(topic) as h: producer.produce(topic, value, headers=list(h.items()))`; `with tracing.consumer_span(topic, dict(msg.headers() or [])):` (bytes values are decoded) |
| Celery | `CeleryInstrumentor().instrument()` in `worker_process_init` (publish side too); pass the context in task headers, not the payload |

`opentelemetry-bootstrap -a install` lists the instrumentation packages that match what is installed.

## Rules and pitfalls

- Use context managers: spans end across exceptions; only the exception **type** is recorded as status.
- Async/thread hand-offs: `contextvars` follow `asyncio` tasks but not `ThreadPoolExecutor`; capture
  `context.get_current()` and `context.attach(ctx)` in the worker, `detach` in `finally`.
- Detailed mode: `with tracing.detail_span("compute", items=n):` is a no-op unless `TRACING_DETAIL=true`.
- Log correlation: `trace_id, span_id = Tracing.ids()` (hex, `('', '')` outside a span); attach both or neither.
  Use `service-logging` (jlogger) when present.
- Fork safety: the batch processor thread does not survive `fork()`; create the provider after forking.
- Unsampled parents are honoured (parent-based): no span is exported but IDs stay valid.

Source: [Python instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/).

## Example usage

- “Trace this Litestar service and its Celery workers into the service graph.”
- “Add peer spans for the ClickHouse and Postgres calls in this pipeline.”
