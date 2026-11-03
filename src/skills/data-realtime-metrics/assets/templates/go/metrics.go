// Package telemetry exports the shared stream_pipeline_* OTLP metrics (see
// references/metric-contract.md). Copy this file into the service, build one Metrics at
// startup, and call the recording methods from the hot path:
//
//	m, err := telemetry.New(ctx, telemetry.Options{
//		Service:     cfg.ServiceName,
//		Environment: "stg",
//		Endpoint:    otlpURL,
//		Ingestion:   true,
//	})
//	m.Received(true)                       // every message that arrives
//	m.Dropped()                            // ... that is deliberately not forwarded
//	m.Published(len(payload), elapsed)     // after the Kafka ack / sink write
//	defer m.Shutdown(ctx)                  // flushes the last export
//
// New marks the process running and counts the restart. The zero Metrics is a safe no-op,
// so tests can pass &telemetry.Metrics{}.
package telemetry

import (
	"context"
	"os"
	"strings"
	"sync/atomic"
	"time"

	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetrichttp"
	"go.opentelemetry.io/otel/metric"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/resource"
)

// Options configures New. An empty Endpoint returns a no-op Metrics.
type Options struct {
	Service     string // the pipeline name, e.g. feed-ws
	Environment string
	Node        string // defaults to the hostname
	Endpoint    string // OTEL_EXPORTER_OTLP_ENDPOINT; /v1/metrics is appended
	Token       string // bearer token for the gateway
	Interval    time.Duration
	Ingestion   bool // adds the feed metrics: connection_active, reconnects_total, in_flight
}

type Metrics struct {
	provider   *sdkmetric.MeterProvider
	messages   metric.Int64Counter
	bytes      metric.Int64Counter
	latency    metric.Float64Histogram
	errors     metric.Int64Counter
	reconnects metric.Int64Counter

	lastInput    atomic.Int64 // unix nanos of the newest live input
	running      atomic.Int64
	connected    atomic.Int64
	kafkaHealthy atomic.Int64
	backlog      atomic.Pointer[func() int]
	inFlight     atomic.Pointer[func() int]
}

var (
	received  = metric.WithAttributes(attribute.String("status", "received"))
	dropped   = metric.WithAttributes(attribute.String("status", "dropped"))
	published = metric.WithAttributes(attribute.String("status", "published"))
)

// latencyBuckets (ms) reach a minute because messages wait in a buffer during a Kafka outage.
var latencyBuckets = []float64{
	1, 2, 5, 10, 20, 50, 100, 250, 500, 1000, 2000, 5000, 10000, 30000, 60000,
}

// newProvider builds the OTLP/HTTP meter provider with the latency buckets and the identity
// resource.
func newProvider(ctx context.Context, o Options) (*sdkmetric.MeterProvider, error) {
	// WithEndpointURL uses the URL as given since otel-go 1.43: append the signal path.
	metricsURL := strings.TrimSuffix(o.Endpoint, "/") + "/v1/metrics"
	opts := []otlpmetrichttp.Option{otlpmetrichttp.WithEndpointURL(metricsURL)}
	if o.Token != "" {
		authorization := map[string]string{"Authorization": "Bearer " + o.Token}
		opts = append(opts, otlpmetrichttp.WithHeaders(authorization))
	}

	exporter, err := otlpmetrichttp.New(ctx, opts...)
	if err != nil {
		return nil, err
	}

	res, err := resource.New(ctx, resource.WithAttributes(
		attribute.String("service.name", o.Service),
		attribute.String("service.namespace", "platform"),
		attribute.String("deployment.environment", o.Environment),
		attribute.String("host.name", o.Node),
	))
	if err != nil {
		return nil, err
	}

	// The view sets the buckets; do not give the histogram a unit (Mimir would rename it).
	reader := sdkmetric.NewPeriodicReader(exporter, sdkmetric.WithInterval(o.Interval))
	latencyView := sdkmetric.NewView(
		sdkmetric.Instrument{Name: "stream_pipeline_latency_ms"},
		sdkmetric.Stream{
			Aggregation: sdkmetric.AggregationExplicitBucketHistogram{Boundaries: latencyBuckets},
		},
	)

	return sdkmetric.NewMeterProvider(
		sdkmetric.WithResource(res),
		sdkmetric.WithReader(reader),
		sdkmetric.WithView(latencyView),
	), nil
}

func New(ctx context.Context, o Options) (*Metrics, error) {
	m := &Metrics{}
	if o.Endpoint == "" {
		return m, nil
	}
	if o.Interval <= 0 {
		o.Interval = 10 * time.Second
	}
	if o.Node == "" {
		o.Node, _ = os.Hostname()
	}
	provider, err := newProvider(ctx, o)
	if err != nil {
		return nil, err
	}
	m.provider = provider

	meter := m.provider.Meter(o.Service)
	m.messages, _ = meter.Int64Counter("stream_pipeline_messages_total")
	m.bytes, _ = meter.Int64Counter("stream_pipeline_payload_bytes_total")
	m.latency, _ = meter.Float64Histogram("stream_pipeline_latency_ms")
	m.errors, _ = meter.Int64Counter("stream_pipeline_errors_total")
	restarts, _ := meter.Int64Counter("stream_pipeline_restarts_total")
	running, _ := meter.Int64ObservableGauge("stream_pipeline_running")
	kafkaUp, _ := meter.Int64ObservableGauge("stream_pipeline_kafka_healthy")
	started, _ := meter.Float64ObservableGauge("stream_pipeline_start_timestamp_seconds")
	age, _ := meter.Float64ObservableGauge("stream_pipeline_last_message_age_ms")
	latest, _ := meter.Float64ObservableGauge("stream_pipeline_latest_event_timestamp_seconds")
	lag, _ := meter.Int64ObservableGauge("stream_pipeline_consumer_lag")
	instruments := []metric.Observable{running, kafkaUp, started, age, latest, lag}
	var connected, inFlight metric.Int64Observable
	if o.Ingestion {
		m.reconnects, _ = meter.Int64Counter("stream_pipeline_reconnects_total")
		connected, _ = meter.Int64ObservableGauge("stream_pipeline_connection_active")
		inFlight, _ = meter.Int64ObservableGauge("stream_pipeline_in_flight")
		instruments = append(instruments, connected, inFlight)
	}
	startedAt := float64(time.Now().UnixNano()) / 1e9
	m.running.Store(1)
	restarts.Add(ctx, 1)
	_, err = meter.RegisterCallback(func(_ context.Context, obs metric.Observer) error {
		obs.ObserveInt64(running, m.running.Load())
		obs.ObserveInt64(kafkaUp, m.kafkaHealthy.Load())
		obs.ObserveFloat64(started, startedAt)
		if last := m.lastInput.Load(); last > 0 {
			obs.ObserveFloat64(age, float64(time.Since(time.Unix(0, last)).Milliseconds()))
			obs.ObserveFloat64(latest, float64(last)/1e9)
		}
		if f := m.backlog.Load(); f != nil {
			obs.ObserveInt64(lag, int64((*f)()))
		}
		if o.Ingestion {
			obs.ObserveInt64(connected, m.connected.Load())
			if f := m.inFlight.Load(); f != nil {
				obs.ObserveInt64(inFlight, int64((*f)()))
			}
		}
		return nil
	}, instruments...)
	return m, err
}

// Shutdown reports running=0 and flushes the final export.
func (m *Metrics) Shutdown(ctx context.Context) error {
	m.running.Store(0)
	m.connected.Store(0)
	if m.provider != nil {
		return m.provider.Shutdown(ctx)
	}
	return nil
}

// SetBacklog reports the messages waiting (Kafka lag for consumers, queue depth for ingestion).
func (m *Metrics) SetBacklog(f func() int) {
	m.backlog.Store(&f)
}

// SetInFlight reports messages handed to the Kafka client and not yet acknowledged (ingestion).
func (m *Metrics) SetInFlight(f func() int) {
	m.inFlight.Store(&f)
}

func (m *Metrics) SetKafkaHealthy(v bool) {
	m.kafkaHealthy.Store(b2i(v))
}

// SetConnected reports whether the feed connection is up (ingestion).
func (m *Metrics) SetConnected(v bool) {
	m.connected.Store(b2i(v))
}

func (m *Metrics) Reconnect() {
	if m.reconnects != nil {
		m.reconnects.Add(context.Background(), 1)
	}
}

// Received counts every arrival. live=false (heartbeats, replays) counts it without
// refreshing the freshness gauges.
func (m *Metrics) Received(live bool) {
	if live {
		m.lastInput.Store(time.Now().UnixNano())
	}
	if m.messages != nil {
		m.messages.Add(context.Background(), 1, received)
	}
}

// Dropped counts a message that arrived but was deliberately not forwarded; call Received for it
// too.
func (m *Metrics) Dropped() {
	if m.messages != nil {
		m.messages.Add(context.Background(), 1, dropped)
	}
}

// Published counts a forwarded message (Kafka ack, sink write, handled); latency runs from arrival.
func (m *Metrics) Published(bytes int, latency time.Duration) {
	if m.messages != nil {
		m.messages.Add(context.Background(), 1, published)
		m.bytes.Add(context.Background(), int64(bytes))
		m.latency.Record(context.Background(), float64(latency.Microseconds())/1000)
	}
}

func (m *Metrics) Error() {
	if m.errors != nil {
		m.errors.Add(context.Background(), 1)
	}
}

func b2i(v bool) int64 {
	if v {
		return 1
	}
	return 0
}
