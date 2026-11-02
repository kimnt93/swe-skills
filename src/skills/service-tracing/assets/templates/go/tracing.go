// Package telemetry sets up service tracing for the dependency graph (see references/go.md and
// references/env.md). Copy this file into internal/telemetry/ and build one *Tracing at startup:
//
//	// Reads SERVICE_NAME, RUN_ENV, OTEL_* ... (references/env.md).
//	opts, err := telemetry.OptionsFromEnv()
//	tr, err := telemetry.New(ctx, opts)
//
//	// A bounded context that outlives request cancellation.
//	defer tr.Shutdown(shutdownCtx)
//
// Default (dependency) mode records boundary spans only. otelhttp/otelgrpc and driver
// instrumentation cover most hops; the helpers below cover the rest and keep peer names stable.
// Every helper returns the new context and an end function: call end(err) once, on every path.
//
//	// Inbound hop (SERVER).
//	ctx, end := tr.ServerSpan(ctx, "POST /orders", propagation.HeaderCarrier(r.Header))
//	defer func() { end(err) }()
//
//	// Datastore (CLIENT).
//	ctx, endDB := tr.PeerSpan(ctx, "postgres", "insert orders")
//
//	// Outbound HTTP call (CLIENT).
//	header := propagation.HeaderCarrier(req.Header)
//	ctx, endHTTP := tr.ClientSpan(ctx, "GET /pricing", "pricing", header)
//
//	// Publish: the message headers carry traceparent.
//	ctx, endPub := tr.ProducerSpan(ctx, "orders.created", carrier)
//
//	// Message handler (CONSUMER).
//	ctx, endMsg := tr.ConsumerSpan(ctx, "orders.created", carrier)
//
// DetailSpan is a no-op unless TRACING_DETAIL=true (detailed mode on request). An empty endpoint,
// OTEL_TRACES_EXPORTER=none or OTEL_SDK_DISABLED=true keeps every call working without a collector.
package telemetry

import (
	"context"
	"errors"
	"fmt"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/trace"
)

// Options configures New. Service is required.
type Options struct {
	// OTEL_SERVICE_NAME, else SERVICE_NAME: one stable logical name per service.
	Service string
	// DEPLOYMENT_ENVIRONMENT, else RUN_ENV, else ENV_NAME, else "local".
	Environment string
	// NODE_NAME; default the hostname (Swarm: "{{.Node.Hostname}}").
	Node string
	// SERVICE_VERSION or service.version in OTEL_RESOURCE_ATTRIBUTES.
	Version string
	// OTLP/HTTP base URL; /v1/traces is appended. Empty = no export.
	Endpoint string
	// Bearer token for the gateway (OTEL_AUTH_TOKEN or the file OTEL_AUTH_TOKEN_FILE).
	Token string
	// OTEL_EXPORTER_OTLP_TIMEOUT (ms), default 5s.
	Timeout time.Duration
	// OTEL_TRACES_SAMPLER, default parentbased_traceidratio.
	Sampler string
	// OTEL_TRACES_SAMPLER_ARG, default 1.0.
	SamplerArg float64
	// TRACING_DETAIL.
	Detail     bool
	Attributes []attribute.KeyValue
	// Tests: an in-memory exporter (used with a synchronous processor).
	Exporter sdktrace.SpanExporter
}

// Tracing owns the provider for this process.
type Tracing struct {
	Tracer   trace.Tracer
	provider *sdktrace.TracerProvider
	opts     Options
}

// End finishes a span: pass the operation's error (or nil). Only the error type is recorded as
// status.
type End func(err error)

// OptionsFromEnv reads the tracing variables documented in references/env.md.
func OptionsFromEnv() (Options, error) {
	service := firstNonEmpty(os.Getenv("OTEL_SERVICE_NAME"), os.Getenv("SERVICE_NAME"))
	if service == "" {
		return Options{}, errors.New("SERVICE_NAME (or OTEL_SERVICE_NAME) is required")
	}
	extra := map[string]string{}
	for _, item := range strings.Split(os.Getenv("OTEL_RESOURCE_ATTRIBUTES"), ",") {
		if k, v, ok := strings.Cut(item, "="); ok {
			extra[strings.TrimSpace(k)] = strings.TrimSpace(v)
		}
	}
	environment := firstNonEmpty(
		os.Getenv("DEPLOYMENT_ENVIRONMENT"),
		os.Getenv("RUN_ENV"),
		os.Getenv("ENV_NAME"),
		"local",
	)
	endpoint := firstNonEmpty(
		strings.TrimSuffix(os.Getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"), "/v1/traces"),
		os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
	)

	o := Options{
		Service:     service,
		Environment: environment,
		Node:        os.Getenv("NODE_NAME"),
		Version:     firstNonEmpty(os.Getenv("SERVICE_VERSION"), extra["service.version"]),
		Endpoint:    endpoint,
		Sampler:     firstNonEmpty(os.Getenv("OTEL_TRACES_SAMPLER"), "parentbased_traceidratio"),
		SamplerArg:  1.0,
		Timeout:     5 * time.Second,
		Detail:      parseBool(os.Getenv("TRACING_DETAIL")),
	}
	delete(extra, "service.version")
	for k, v := range extra {
		o.Attributes = append(o.Attributes, attribute.String(k, v))
	}
	token, err := secret("OTEL_AUTH_TOKEN")
	if err != nil {
		return Options{}, err
	}
	o.Token = token
	if v := os.Getenv("OTEL_TRACES_SAMPLER_ARG"); v != "" {
		if o.SamplerArg, err = strconv.ParseFloat(v, 64); err != nil {
			return Options{}, fmt.Errorf("OTEL_TRACES_SAMPLER_ARG: %w", err)
		}
	}
	if v := os.Getenv("OTEL_EXPORTER_OTLP_TIMEOUT"); v != "" {
		ms, err := strconv.Atoi(v)
		if err != nil {
			return Options{}, fmt.Errorf("OTEL_EXPORTER_OTLP_TIMEOUT: %w", err)
		}
		o.Timeout = time.Duration(ms) * time.Millisecond
	}
	return o, nil
}

// New builds the provider, registers it and the W3C propagators globally, and returns the tracing
// handle.
func New(ctx context.Context, o Options) (*Tracing, error) {
	if o.Service == "" {
		return nil, errors.New("telemetry: Service is required")
	}
	if o.Node == "" {
		o.Node, _ = os.Hostname()
	}
	if o.Environment == "" {
		o.Environment = "local"
	}

	res, err := resource.New(ctx, resource.WithAttributes(resourceAttributes(o)...))
	if err != nil {
		return nil, err
	}

	sampler, err := newSampler(o)
	if err != nil {
		return nil, err
	}

	opts := []sdktrace.TracerProviderOption{
		sdktrace.WithResource(res),
		sdktrace.WithSampler(sampler),
	}

	exporterOpt, err := exporterOption(ctx, o)
	if err != nil {
		return nil, err
	}
	if exporterOpt != nil {
		opts = append(opts, exporterOpt)
	}

	tp := sdktrace.NewTracerProvider(opts...)
	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{},
		propagation.Baggage{},
	))

	return &Tracing{Tracer: tp.Tracer("service-tracing"), provider: tp, opts: o}, nil
}

// resourceAttributes is the identity every span carries.
func resourceAttributes(o Options) []attribute.KeyValue {
	attrs := []attribute.KeyValue{
		attribute.String("service.name", o.Service),
		attribute.String("deployment.environment", o.Environment),
		attribute.String("deployment.environment.name", o.Environment),
		attribute.String("host.name", o.Node),
		attribute.String("service.instance.id", fmt.Sprintf("%s-%d", o.Node, os.Getpid())),
	}
	if o.Version != "" {
		attrs = append(attrs, attribute.String("service.version", o.Version))
	}

	return append(attrs, o.Attributes...)
}

// exporterOption picks how spans leave the process: a synchronous test exporter, the OTLP/HTTP
// batcher, or nothing (the tracer still works and records no export).
func exporterOption(ctx context.Context, o Options) (sdktrace.TracerProviderOption, error) {
	if o.Exporter != nil {
		// Tests: deterministic, no batching.
		return sdktrace.WithSyncer(o.Exporter), nil
	}

	exportEnabled := o.Endpoint != "" &&
		os.Getenv("OTEL_TRACES_EXPORTER") != "none" &&
		!parseBool(os.Getenv("OTEL_SDK_DISABLED"))
	if !exportEnabled {
		return nil, nil
	}

	// WithEndpointURL uses the URL as given since otel-go 1.43: append the signal path.
	tracesURL := strings.TrimSuffix(o.Endpoint, "/") + "/v1/traces"
	eo := []otlptracehttp.Option{otlptracehttp.WithEndpointURL(tracesURL)}
	if o.Token != "" {
		authorization := map[string]string{"Authorization": "Bearer " + o.Token}
		eo = append(eo, otlptracehttp.WithHeaders(authorization))
	}
	if o.Timeout > 0 {
		eo = append(eo, otlptracehttp.WithTimeout(o.Timeout))
	}

	exp, err := otlptracehttp.New(ctx, eo...)
	if err != nil {
		return nil, err
	}

	// Batch export off the request path; queue/batch sizes come from the OTEL_BSP_* variables.
	return sdktrace.WithBatcher(exp), nil
}

// Shutdown flushes buffered spans; use a bounded context that outlives request cancellation.
func (t *Tracing) Shutdown(ctx context.Context) error {
	return t.provider.Shutdown(ctx)
}

// ServerSpan continues the caller's trace from the inbound carrier (missing/invalid context starts
// a new trace).
func (t *Tracing) ServerSpan(
	ctx context.Context,
	name string,
	in propagation.TextMapCarrier,
	attrs ...attribute.KeyValue,
) (context.Context, End) {
	// A nil carrier means "no inbound context".
	if in != nil {
		ctx = otel.GetTextMapPropagator().Extract(ctx, in)
	}

	return t.start(ctx, name, trace.SpanKindServer, attrs...)
}

// ClientSpan wraps a call to another service and injects the context into the outgoing carrier.
func (t *Tracing) ClientSpan(
	ctx context.Context,
	name, peer string,
	out propagation.TextMapCarrier,
	attrs ...attribute.KeyValue,
) (context.Context, End) {
	all := append([]attribute.KeyValue{attribute.String("peer.service", peer)}, attrs...)

	ctx, end := t.start(ctx, name, trace.SpanKindClient, all...)
	otel.GetTextMapPropagator().Inject(ctx, out)

	return ctx, end
}

// PeerSpan wraps a call to a datastore/broker/object store that has no instrumentation of its own,
// with a stable peer identity. Host and port come from the infrastructure variables (POSTGRES_HOST,
// KAFKA_BOOTSTRAP_SERVERS...).
func (t *Tracing) PeerSpan(
	ctx context.Context,
	kind, operation string,
	attrs ...attribute.KeyValue,
) (context.Context, End) {
	upperKind := strings.ToUpper(kind)

	p, ok := peers[kind]
	if !ok {
		p = peer{
			system: attribute.String("rpc.system", kind),
			kind:   trace.SpanKindClient,
			prefix: upperKind,
		}
	}

	host, port := peerAddress(kind, p.prefix)
	peerService := firstNonEmpty(os.Getenv("PEER_SERVICE_"+upperKind), kind)

	all := []attribute.KeyValue{
		attribute.String("peer.service", peerService),
		p.system,
	}
	if host != "" {
		all = append(all, attribute.String("server.address", host))
	}
	if port != 0 {
		all = append(all, attribute.Int("server.port", port))
	}
	return t.start(ctx, kind+" "+operation, p.kind, append(all, attrs...)...)
}

// ProducerSpan wraps a publish and injects the context into the message headers.
func (t *Tracing) ProducerSpan(
	ctx context.Context,
	destination string,
	out propagation.TextMapCarrier,
	attrs ...attribute.KeyValue,
) (context.Context, End) {
	peerService := firstNonEmpty(os.Getenv("PEER_SERVICE_KAFKA"), "kafka")

	all := append([]attribute.KeyValue{
		attribute.String("messaging.system", "kafka"),
		attribute.String("messaging.destination.name", destination),
		attribute.String("messaging.operation", "publish"),
		attribute.String("peer.service", peerService),
	}, attrs...)

	ctx, end := t.start(ctx, destination+" publish", trace.SpanKindProducer, all...)
	otel.GetTextMapPropagator().Inject(ctx, out)

	return ctx, end
}

// ConsumerSpan handles one message with the producer's context from the message headers as parent.
func (t *Tracing) ConsumerSpan(
	ctx context.Context,
	destination string,
	in propagation.TextMapCarrier,
	attrs ...attribute.KeyValue,
) (context.Context, End) {
	if in != nil {
		ctx = otel.GetTextMapPropagator().Extract(ctx, in)
	}

	all := append([]attribute.KeyValue{
		attribute.String("messaging.system", "kafka"),
		attribute.String("messaging.destination.name", destination),
		attribute.String("messaging.operation", "process"),
	}, attrs...)

	return t.start(ctx, destination+" process", trace.SpanKindConsumer, all...)
}

// DetailSpan is an internal span for detailed mode; a no-op unless TRACING_DETAIL=true.
func (t *Tracing) DetailSpan(
	ctx context.Context,
	name string,
	attrs ...attribute.KeyValue,
) (context.Context, End) {
	if !t.opts.Detail {
		return ctx, func(error) {}
	}
	return t.start(ctx, name, trace.SpanKindInternal, attrs...)
}

// IDs returns the trace and span IDs of the active valid span, for log correlation ("" , ""
// otherwise).
func IDs(ctx context.Context) (traceID, spanID string) {
	sc := trace.SpanContextFromContext(ctx)
	if !sc.IsValid() {
		return "", ""
	}
	return sc.TraceID().String(), sc.SpanID().String()
}

func (t *Tracing) start(
	ctx context.Context,
	name string,
	kind trace.SpanKind,
	attrs ...attribute.KeyValue,
) (context.Context, End) {
	ctx, span := t.Tracer.Start(ctx, name, trace.WithSpanKind(kind), trace.WithAttributes(attrs...))
	var done bool
	return ctx, func(err error) {
		if done {
			return
		}
		done = true
		if err != nil {
			// Type only: error messages can carry payloads or credentials.
			span.SetStatus(codes.Error, fmt.Sprintf("%T", err))
			span.RecordError(
				err,
				trace.WithAttributes(attribute.Bool("exception.escaped", true)),
				trace.WithStackTrace(false),
			)
		}
		span.End()
	}
}

type peer struct {
	system attribute.KeyValue
	kind   trace.SpanKind
	prefix string
}

var peers = map[string]peer{
	"postgres":   {attribute.String("db.system", "postgresql"), trace.SpanKindClient, "POSTGRES"},
	"redis":      {attribute.String("db.system", "redis"), trace.SpanKindClient, "REDIS"},
	"clickhouse": {attribute.String("db.system", "clickhouse"), trace.SpanKindClient, "CLICKHOUSE"},
	"kafka":      {attribute.String("messaging.system", "kafka"), trace.SpanKindProducer, "KAFKA"},
	"s3":         {attribute.String("rpc.system", "aws-api"), trace.SpanKindClient, "S3"},
}

func peerAddress(kind, prefix string) (string, int) {
	switch kind {
	case "kafka":
		first := strings.TrimSpace(strings.Split(os.Getenv("KAFKA_BOOTSTRAP_SERVERS"), ",")[0])
		host, port, found := strings.Cut(first, ":")
		if !found {
			return first, 0
		}
		n, _ := strconv.Atoi(port)
		return host, n
	case "s3":
		u, err := url.Parse(os.Getenv("S3_ENDPOINT"))
		if err != nil || u.Hostname() == "" {
			return "", 0
		}
		if n, err := strconv.Atoi(u.Port()); err == nil {
			return u.Hostname(), n
		}
		if u.Scheme == "https" {
			return u.Hostname(), 443
		}
		return u.Hostname(), 80
	}
	defaults := map[string]int{"postgres": 5432, "redis": 6379, "clickhouse": 9000}
	port := defaults[kind]
	if n, err := strconv.Atoi(os.Getenv(prefix + "_PORT")); err == nil {
		port = n
	}
	return os.Getenv(prefix + "_HOST"), port
}

func newSampler(o Options) (sdktrace.Sampler, error) {
	switch strings.ToLower(o.Sampler) {
	case "always_on":
		return sdktrace.AlwaysSample(), nil
	case "parentbased_always_on":
		return sdktrace.ParentBased(sdktrace.AlwaysSample()), nil
	case "always_off":
		return sdktrace.NeverSample(), nil
	case "parentbased_always_off":
		return sdktrace.ParentBased(sdktrace.NeverSample()), nil
	}
	if o.SamplerArg < 0 || o.SamplerArg > 1 {
		return nil, fmt.Errorf("OTEL_TRACES_SAMPLER_ARG must be within 0..1, got %v", o.SamplerArg)
	}
	if strings.EqualFold(o.Sampler, "traceidratio") {
		return sdktrace.TraceIDRatioBased(o.SamplerArg), nil
	}

	// The default honours the upstream sampling decision.
	return sdktrace.ParentBased(sdktrace.TraceIDRatioBased(o.SamplerArg)), nil
}

// secret returns NAME, else the contents of the file named by NAME_FILE.
func secret(name string) (string, error) {
	if v := strings.TrimSpace(os.Getenv(name)); v != "" {
		return v, nil
	}
	if path := os.Getenv(name + "_FILE"); path != "" {
		b, err := os.ReadFile(path)
		if err != nil {
			return "", fmt.Errorf("%s_FILE: %w", name, err)
		}
		return strings.TrimSpace(string(b)), nil
	}
	return "", nil
}

func parseBool(v string) bool {
	switch strings.ToLower(strings.TrimSpace(v)) {
	case "1", "true", "yes", "on":
		return true
	}
	return false
}

func firstNonEmpty(values ...string) string {
	for _, v := range values {
		if v != "" {
			return v
		}
	}
	return ""
}
