# Python + Kafka (confluent-kafka)

*Verified with: confluent-kafka 2.15 and Apache Kafka 4.1 in the scaffold template (live publish/consume test, ruff and pycodestyle clean).*

Reference: `assets/template/src/service/messaging/kafka.py`, `assets/template/src/service/settings/`, `assets/env/kafka.env.example` (tested in the scaffold template). PEP 8 style (79 columns).

## Environment (load from env)

```bash
# assets/env/kafka.env.example
KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092  KAFKA_SECURITY_PROTOCOL=PLAINTEXT  KAFKA_CONSUMER_GROUP=example-service-local
KAFKA_SASL_MECHANISM=SCRAM-SHA-256  KAFKA_SASL_USERNAME=
KAFKA_SASL_PASSWORD=     # SECRET, required only for SASL_*: no default, never committed; Swarm: KAFKA_SASL_PASSWORD_FILE
```

```python
from service.settings import KafkaSettings         # assets/template/src/service/settings/kafka.py (+ _base.py)

settings = KafkaSettings()      # SASL_* without username+password fails by name; kafka_client_config() builds the librdkafka dict
```

## Producer

- `Producer({**settings.kafka_client_config(), "enable.idempotence": True, "acks": "all", "linger.ms": 5, "compression.type": "lz4"})`:
  retries cannot duplicate or lose.
- confluent-kafka is **synchronous**: poll on a background thread and resolve an `asyncio.Future` from the delivery callback
  (`call_soon_threadsafe`), so `await publish(...)` returns only when the broker acknowledged. Never call `produce` and ignore delivery.
- Shutdown: `flush(timeout)` then stop the poll thread. Keys decide ordering (same key, same partition); say which you use.
- Forward raw `bytes`; encode your own events with `msgspec.json.encode(Struct)`. Put `traceparent`/`origin` in headers, not payloads.
- Topic names follow the project convention (for example `{RUN_ENV}.{service}.{stage}`); create topics (with the intended partition count)
  **before** the service starts.

## Consumer

- `enable.auto.commit=False`; commit **after** the handler succeeds; handlers are idempotent (`ON CONFLICT`), because a crash re-delivers.
- `consumer.poll` blocks: run it in an executor (`loop.run_in_executor`) so the event loop stays free; stop on an `asyncio.Event`;
  `consumer.close()` in `finally` so the group is left cleanly.
- Decode with a reused `msgspec.json.Decoder(Type)` (typed, validated, no dict round trip).
- **Create the topic first:** a subscription to a missing topic is not noticed until the next metadata refresh (5 minutes by default).
- Poison messages: after N attempts publish to `<topic>.dlq` with the error type and origin headers, commit, alert via metrics
  (`data-realtime-metrics`).
- One consumer group per logical consumer (`KAFKA_CONSUMER_GROUP`, include the plane); scale by partitions.

## Operations

A single-node broker needs seconds after start: gate with `scripts/health.sh --wait kafka` (also in integration tests). The wheel bundles
librdkafka (no system packages needed on glibc images).

## Example usage

- “Write a consumer process that upserts ticks into Postgres with at-least-once delivery.”
- “Publish order events with the trace context in headers.”
