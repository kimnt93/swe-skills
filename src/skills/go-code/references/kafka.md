# Go + Kafka (confluent-kafka-go v2)

*Verified with: confluent-kafka-go v2.15 (bundled librdkafka) on Apache Kafka 4.1 (scaffold e2e publish/consume test).*

Reference: `assets/template/internal/infrastructure/kafkax/kafka.go`, `assets/template/internal/config/` (env loader), `assets/env/kafka.env.example` (the same code is compiled and
tested against a live broker in the scaffold template).

## Environment (load from env)

```bash
# assets/env/kafka.env.example
KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092   KAFKA_SECURITY_PROTOCOL=PLAINTEXT   KAFKA_CONSUMER_GROUP=example-service-local
KAFKA_SASL_MECHANISM=SCRAM-SHA-256   KAFKA_SASL_USERNAME=
KAFKA_SASL_PASSWORD=     # SECRET, required only for SASL_*: no default, never committed; Swarm: KAFKA_SASL_PASSWORD_FILE
```

```go
l := config.NewLoader(nil)
kcfg := config.LoadKafka(l)            // assets/template/internal/config/kafka.go: SASL_* needs username + password, else a named error
if err := l.Err(); err != nil { return err }
producer, err := kafkax.NewProducer(kcfg)   // SASL settings are added only for SASL_* protocols
```

## Producer

```go
kafka.NewProducer(&kafka.ConfigMap{"bootstrap.servers": s, "enable.idempotence": true, "acks": "all",
    "linger.ms": 5, "compression.type": "lz4"})
```

- **Idempotent + `acks=all`** by default: retries cannot duplicate or lose.
- **Know when it is acknowledged.** `Produce` only enqueues. For request paths wait for the delivery report
  (`Produce(msg, deliveryChan)`, as `Publish` does). For throughput, produce asynchronously and consume `p.Events()` in
  one goroutine: count success, log and count failures, and **stop ingestion on persistent broker failure** instead of
  buffering forever.
- **Drain on shutdown:** `Flush(timeoutMs)` then `Close()`; shutdown order is stop input -> flush -> close.
- **Keys decide ordering.** Same key -> same partition -> ordered. Round-robin (`nil` key) balances load but loses
  per-key order; choose deliberately and document it.
- **Payloads:** forward raw `[]byte` unchanged (do not re-marshal); if you need to describe it use headers
  (`source`, `origin=topic:partition:offset`, `traceparent`). Keep messages well under the broker limit.
- **Topic names** follow the project convention (for example `{RUN_ENV}.{service}.{stage}`); create topics with the intended
  partition count **before** the service starts (a pipeline reads partition metadata once and must be restarted after
  an increase).

## Consumer

- `enable.auto.commit=false`; commit **after** the handler succeeds (`CommitMessage`). A crash re-delivers, so handlers
  are idempotent (deterministic ids, upserts, `ON CONFLICT`).
- `auto.offset.reset`: `latest` for live-only consumers, `earliest` for replay-capable ones; state which.
- **One group per logical consumer** (`KAFKA_CONSUMER_GROUP`, include the plane); scale by partitions, not threads.
- **Create the topic first.** A subscription to a topic that does not exist yet is not noticed until the next metadata
  refresh (5 minutes by default): seed the topic in tests and provision it in deployments.
- `ReadMessage(timeout)` loop with `ErrTimedOut` as the idle case; stop on `ctx.Done()`; always `defer Close()` so the
  group leaves cleanly (a restarted consumer otherwise waits for the session timeout to rejoin, about 45 s).
- Poison messages: do not loop forever. After N attempts publish to a `.dlq` topic with the error type and origin
  headers, commit, and alert via metrics.

## Operations

- Build with cgo: `CGO_ENABLED=1`; the runtime image needs `libstdc++6` and `ca-certificates` (`deployment-setup`
  Go Dockerfile). Static `CGO_ENABLED=0` builds cannot use this client; use `segmentio/kafka-go` only if a pure-Go
  build is a hard requirement.
- Start-up waits for the broker through `scripts/health.sh --wait kafka` (a single-node broker needs seconds before its
  transaction coordinator accepts idempotent producers).
- Metrics: `data-realtime-metrics` contract (`received`, `dropped`, `published`, lag). Tracing: producer and consumer spans
  with the context in message headers (`service-tracing`).

## Testing

Unit-test handlers with plain `*kafka.Message` values. Round trips need a real broker
(`-tags integration`, `docker-compose.infra.local.yaml up -d kafka`): seed the topic, start the consumer, publish until it
receives, assert key and value.

## Example usage

- “Write a consumer that upserts messages into Postgres with at-least-once delivery.”
- “Publish order events with the trace context in headers.”
