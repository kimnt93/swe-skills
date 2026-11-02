# Go

Template: `assets/templates/go/tracing.go` (`package telemetry`; copy to `internal/telemetry/`). Tests and demo:
`assets/templates/go/smoke_test.go`. Tested with Go 1.26 and otel-go 1.47 (`go test -race`).

```bash
go get go.opentelemetry.io/otel go.opentelemetry.io/otel/sdk \
  go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp
```

## Wire it

```go
opts, err := telemetry.OptionsFromEnv()          // OTEL_SERVICE_NAME|SERVICE_NAME, RUN_ENV, OTEL_* (references/env.md)
if err != nil { return err }
tr, err := telemetry.New(ctx, opts)              // provider + W3C propagators registered globally
if err != nil { return err }
defer func() {                                   // bounded context that outlives request cancellation
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second); defer cancel()
    _ = tr.Shutdown(ctx)
}()
```

Initialise before the HTTP server, clients and consumers start; shut down after they stop accepting work.

## Boundary spans (dependency mode)

| Hop | Use |
|---|---|
| Inbound HTTP | `otelhttp.NewHandler(mux, "server")`, or `tr.ServerSpan(ctx, route, propagation.HeaderCarrier(r.Header))`. Fiber: `otelfiber` middleware; Gin: `otelgin`; gRPC: `otelgrpc` stats handlers |
| Outbound HTTP | `otelhttp.NewTransport(http.DefaultTransport)` on the client, or `tr.ClientSpan(ctx, "GET /pricing", "pricing", propagation.HeaderCarrier(req.Header))` |
| PostgreSQL (`go-pg` v10, `pgx`) | pgx: `otelpgx` tracer. go-pg has no maintained OTel hook: wrap the calls (or a `QueryHook`) with `tr.PeerSpan(ctx, "postgres", "select orders")` |
| Redis (`go-redis` v9) | `redisotel.InstrumentTracing(rdb)`; otherwise `tr.PeerSpan(ctx, "redis", "get")` |
| ClickHouse, S3/RustFS | `tr.PeerSpan(ctx, "clickhouse", "insert trades")`, `tr.PeerSpan(ctx, "s3", "put object")` |
| Kafka (`confluent-kafka-go`) | `tr.ProducerSpan(ctx, topic, carrier)` then copy the carrier into `kafka.Message.Headers`; `tr.ConsumerSpan(ctx, topic, carrier)` per message (adapter below) |

Confluent headers adapter (the carrier interface is `Get/Set/Keys`):

```go
type kafkaCarrier struct{ h *[]kafka.Header }
func (c kafkaCarrier) Get(k string) string { for _, h := range *c.h { if h.Key == k { return string(h.Value) } }; return "" }
func (c kafkaCarrier) Set(k, v string)     { *c.h = append(*c.h, kafka.Header{Key: k, Value: []byte(v)}) }
func (c kafkaCarrier) Keys() []string      { ks := make([]string, 0, len(*c.h)); for _, h := range *c.h { ks = append(ks, h.Key) }; return ks }
// produce: ctx, end := tr.ProducerSpan(ctx, topic, kafkaCarrier{&msg.Headers}); err := p.Produce(&msg, nil); end(err)
// consume: ctx, end := tr.ConsumerSpan(ctx, topic, kafkaCarrier{&msg.Headers}); defer func() { end(err) }()
```

End the producer span when the **delivery report** confirms (not when `Produce` returns) if completion defines
the operation. High-throughput feeds: do not span every message; propagate headers and sample.

## Rules and pitfalls

- Pass `context.Context` through handlers, clients and repositories, and use the context returned by the
  helper; a dropped context splits the trace and removes the edge.
- `end(err)` exactly once, on every path (`defer func() { end(err) }()` with a named result). Only the error
  type is recorded as status; never put messages, payloads or SQL text in spans.
- Detailed mode: `tr.DetailSpan(ctx, "compute", attribute.Int("items", n))` is a no-op unless `TRACING_DETAIL=true`.
- Log correlation (zerolog): `traceID, spanID := telemetry.IDs(ctx)`; add both together or neither
  (`log.Ctx(ctx)` with a hook). Use the `service-logging` skill's logger when present.
- Unsampled spans still have valid IDs; the backend stores nothing for them.
- `WithEndpointURL` uses the URL as given: the template appends `/v1/traces` to the base endpoint.

Source: [Go instrumentation](https://opentelemetry.io/docs/languages/go/instrumentation/).

## Example usage

- “Add tracing to this Fiber service so it shows in the service graph.”
- “Propagate trace context through this confluent-kafka producer and consumer.”
