# Go

Template: `assets/templates/go/metrics.go` (`package telemetry`; copy it into `internal/telemetry/`).
Smoke test: `assets/templates/go/smoke_test.go`.

Tested with Go 1.26 and otel-go 1.47.

```bash
go get go.opentelemetry.io/otel go.opentelemetry.io/otel/sdk/metric \
  go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetrichttp
```

## Wire it

```go
metrics, err := telemetry.New(ctx, telemetry.Options{
    Service: cfg.ServiceName, Environment: cfg.Environment, Node: cfg.NodeName,
    Endpoint: cfg.OTLPEndpoint, Token: cfg.OTLPToken, Interval: 10 * time.Second,
    Ingestion: true, // feed -> Kafka services
})
if err != nil { return err }
defer metrics.Shutdown(shutdownCtx)   // flush + running=0
metrics.SetBacklog(func() int { return len(queue) })
metrics.SetInFlight(producer.Len)     // confluent-kafka-go
```

Feed handler (ingestion):

```go
metrics.Received(true)                 // false for heartbeats/control frames and retained replays
if skip(msg) { metrics.Dropped(); return }
queue <- Event{Raw: payload, ReceivedAt: time.Now()}
```

Kafka delivery loop (confluent-kafka-go); pass the arrival time as `Opaque`:

```go
case *kafka.Message:
    if msg.TopicPartition.Error != nil { metrics.Error(); continue }
    started, _ := msg.Opaque.(time.Time)
    metrics.Published(len(msg.Value), time.Since(started))
```

Health probe goroutine (every 5 s):

```go
md, err := producer.GetMetadata(&topic, false, 3000)
tm, ok := md.Topics[topic]
metrics.SetKafkaHealthy(err == nil && ok && tm.Error.Code() == kafka.ErrNoError && len(tm.Partitions) > 0)
```

Connection hooks: `metrics.SetConnected(true)` after the handshake, `defer SetConnected(false)`,
`metrics.Reconnect()` per retry.

## Gotchas

- `WithEndpointURL` uses the URL exactly as given since otel-go 1.43 (older releases appended
  the default path). The template appends `/v1/metrics`; keep that when bumping versions.
- Buckets are set with a `View`, not on the instrument. Leave the histogram without a unit.
- The zero `&telemetry.Metrics{}` is a safe no-op: pass it in unit tests. Instruments are
  created only when an endpoint is set.
- Callbacks run on the SDK's goroutine: `SetBacklog`/`SetInFlight` take functions that must be
  cheap and thread-safe (`len(chan)`, atomic loads). The template stores them atomically.
- `Shutdown` returns an error if the last export fails; log it, do not fail the process.

## Verify

```bash
python3 scripts/otlp_check.py --role ingestion --wait 30 &
OTLP_SMOKE_ENDPOINT=http://127.0.0.1:4318 OTLP_SMOKE_ROLE=ingestion go test -count=1 -run TestSmoke ./internal/telemetry
```
