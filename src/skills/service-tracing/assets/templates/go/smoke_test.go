package telemetry

import (
	"context"
	"errors"
	"fmt"
	"os"
	"strings"
	"testing"

	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/trace/tracetest"
	"go.opentelemetry.io/otel/trace"
)

func newTracing(
	t *testing.T,
	service string,
	detail bool,
) (*Tracing, *tracetest.InMemoryExporter) {
	t.Helper()

	exp := tracetest.NewInMemoryExporter()
	tr, err := New(context.Background(), Options{
		Service:     service,
		Environment: "test",
		Node:        "n1",
		Version:     "1.2.3",
		Exporter:    exp,
		Detail:      detail,
		SamplerArg:  1,
	})
	if err != nil {
		t.Fatal(err)
	}
	return tr, exp
}

func find(
	t *testing.T,
	exp *tracetest.InMemoryExporter,
	kind trace.SpanKind,
	name string,
) tracetest.SpanStub {
	t.Helper()
	for _, s := range exp.GetSpans() {
		if s.SpanKind == kind && (name == "" || s.Name == name) {
			return s
		}
	}
	t.Fatalf("no %v span %q in %v", kind, name, exp.GetSpans())
	return tracetest.SpanStub{}
}

func TestDependencyEdges(t *testing.T) {
	t.Setenv("POSTGRES_HOST", "db.internal")
	t.Setenv("KAFKA_BOOTSTRAP_SERVERS", "k1:9092,k2:9092")
	web, webSpans := newTracing(t, "web", false)
	api, apiSpans := newTracing(t, "api", false)
	ctx := context.Background()

	// web CLIENT -> headers -> api SERVER: one trace, parent = the client span
	h := propagation.MapCarrier{}
	ctx, endClient := web.ClientSpan(ctx, "GET /orders", "api", h)
	if h.Get("traceparent") == "" {
		t.Fatal("client span must inject traceparent")
	}
	sctx, endServer := api.ServerSpan(context.Background(), "GET /orders", h)
	_, endDB := api.PeerSpan(sctx, "postgres", "select orders")
	endDB(nil)
	endServer(nil)
	endClient(nil)
	_ = ctx

	client := find(t, webSpans, trace.SpanKindClient, "")
	server := find(t, apiSpans, trace.SpanKindServer, "")

	sameTrace := server.SpanContext.TraceID() == client.SpanContext.TraceID()
	isChild := server.Parent.SpanID() == client.SpanContext.SpanID()
	if !sameTrace || !isChild {
		t.Fatalf("server span must be a child of the caller's client span: %v vs %v",
			server.Parent, client.SpanContext)
	}
	if v := resourceAttr(server, "service.name"); v != "api" {
		t.Fatalf("service.name = %q", v)
	}
	if resourceAttr(client, "deployment.environment") != "test" {
		t.Fatal("deployment.environment missing")
	}
	if resourceAttr(client, "service.version") != "1.2.3" {
		t.Fatal("service.version missing")
	}

	// peer identity for an uninstrumented datastore
	db := find(t, apiSpans, trace.SpanKindClient, "postgres select orders")
	got := attrs(db)
	want := map[string]string{
		"peer.service":   "postgres",
		"db.system":      "postgresql",
		"server.address": "db.internal",
		"server.port":    "5432",
	}
	for key, value := range want {
		if got[key] != value {
			t.Fatalf("peer attribute %s = %q, want %q (all: %v)", key, got[key], value, got)
		}
	}

	// messaging: producer -> headers -> consumer
	msg := propagation.MapCarrier{}
	_, endPub := web.ProducerSpan(context.Background(), "orders.created", msg)
	endPub(nil)
	_, endCons := api.ConsumerSpan(context.Background(), "orders.created", msg)
	endCons(nil)
	producer := find(t, webSpans, trace.SpanKindProducer, "")
	consumer := find(t, apiSpans, trace.SpanKindConsumer, "")

	isChild = consumer.Parent.SpanID() == producer.SpanContext.SpanID()
	sameTrace = consumer.SpanContext.TraceID() == producer.SpanContext.TraceID()
	if !isChild || !sameTrace {
		t.Fatal("consumer must be a child of the producer span")
	}

	// missing or invalid context starts a valid new trace
	before := len(apiSpans.GetSpans())
	zeroTraceparent := "00-" + strings.Repeat("0", 32) + "-" + strings.Repeat("0", 16) + "-01"
	badCarriers := []propagation.MapCarrier{
		nil,
		{},
		{"traceparent": "garbage"},
		{"traceparent": zeroTraceparent},
	}

	for _, bad := range badCarriers {
		c, end := api.ServerSpan(context.Background(), "GET /bad", bad)
		if !trace.SpanContextFromContext(c).IsValid() {
			t.Fatal("expected a valid new span context")
		}
		end(nil)
	}
	roots := 0
	for _, s := range apiSpans.GetSpans()[before:] {
		if !s.Parent.IsValid() {
			roots++
		}
	}
	if roots != 4 {
		t.Fatalf("roots = %d", roots)
	}

	// failures: error status carries the type, never the message
	_, end := api.ServerSpan(context.Background(), "POST /fail", nil)
	end(errors.New("secret-token-123"))
	failed := apiSpans.GetSpans()[len(apiSpans.GetSpans())-1]
	if failed.Status.Code.String() != "Error" {
		t.Fatalf("status = %+v", failed.Status)
	}
	if strings.Contains(failed.Status.Description, "secret") {
		t.Fatalf("the status must not carry the error message: %+v", failed.Status)
	}

	// kafka peer: first bootstrap server
	_, endK := api.PeerSpan(context.Background(), "kafka", "send")
	endK(nil)
	k := apiSpans.GetSpans()[len(apiSpans.GetSpans())-1]
	if k.SpanKind != trace.SpanKindProducer || attrs(k)["server.address"] != "k1" {
		t.Fatalf("kafka peer: %v", attrs(k))
	}
}

func TestDetailGatedByMode(t *testing.T) {
	api, spans := newTracing(t, "api", false)
	ctx, end := api.ServerSpan(context.Background(), "GET /x", nil)
	_, endD := api.DetailSpan(ctx, "compute")
	endD(nil)
	end(nil)
	for _, s := range spans.GetSpans() {
		if s.SpanKind == trace.SpanKindInternal {
			t.Fatal("dependency mode must not record internal spans")
		}
	}
	det, dspans := newTracing(t, "api", true)
	ctx, end = det.ServerSpan(context.Background(), "GET /x", nil)
	_, endD = det.DetailSpan(ctx, "compute")
	endD(nil)
	end(nil)
	find(t, dspans, trace.SpanKindInternal, "compute")
}

func TestOptionsFromEnv(t *testing.T) {
	if _, err := OptionsFromEnv(); err == nil {
		t.Fatal("SERVICE_NAME must be required")
	}
	dir := t.TempDir()
	tokenFile := dir + "/token"
	_ = os.WriteFile(tokenFile, []byte("tok\n"), 0o600)
	t.Setenv("SERVICE_NAME", "svc")
	t.Setenv("RUN_ENV", "stg")
	t.Setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-gateway:4318")
	t.Setenv("OTEL_AUTH_TOKEN_FILE", tokenFile)
	t.Setenv("OTEL_TRACES_SAMPLER_ARG", "0.25")
	t.Setenv("OTEL_RESOURCE_ATTRIBUTES", "service.version=9.9,team=core")
	o, err := OptionsFromEnv()
	if err != nil {
		t.Fatal(err)
	}
	if o.Service != "svc" || o.Environment != "stg" || o.Version != "9.9" {
		t.Fatalf("identity: %+v", o)
	}
	if o.Token != "tok" || o.SamplerArg != 0.25 || len(o.Attributes) != 1 {
		t.Fatalf("export settings: %+v", o)
	}
	t.Setenv("OTEL_TRACES_SAMPLER_ARG", "7")
	o, _ = OptionsFromEnv()
	if _, err := New(context.Background(), o); err == nil {
		t.Fatal("a ratio outside 0..1 must be rejected")
	}
}

// TestDemo exports one demo request to OTEL_EXPORTER_OTLP_ENDPOINT (see
// references/verification.md):
//
//	DEMO=1 SERVICE_NAME=api TRACEPARENT=<from upstream> DEMO_CALL=worker DEMO_DB=postgres \
//	  go test -run TestDemo -v
func TestDemo(t *testing.T) {
	if os.Getenv("DEMO") == "" {
		t.Skip("set DEMO=1")
	}
	o, err := OptionsFromEnv()
	if err != nil {
		t.Fatal(err)
	}
	tr, err := New(context.Background(), o)
	if err != nil {
		t.Fatal(err)
	}
	in := propagation.MapCarrier{}
	if tp := os.Getenv("TRACEPARENT"); tp != "" {
		in["traceparent"] = tp
	}
	ctx, end := tr.ServerSpan(context.Background(), "GET /demo", in)
	if db := os.Getenv("DEMO_DB"); db != "" {
		_, endDB := tr.PeerSpan(ctx, db, "query")
		endDB(nil)
	}
	if peer := os.Getenv("DEMO_CALL"); peer != "" {
		out := propagation.MapCarrier{}
		_, endC := tr.ClientSpan(ctx, "GET /demo", peer, out)
		fmt.Println("TRACEPARENT=" + out.Get("traceparent"))
		endC(nil)
	}
	end(nil)
	if err := tr.Shutdown(context.Background()); err != nil {
		t.Fatal(err)
	}
}

func resourceAttr(s tracetest.SpanStub, key string) string {
	for _, kv := range s.Resource.Attributes() {
		if string(kv.Key) == key {
			return kv.Value.Emit()
		}
	}
	return ""
}

func attrs(s tracetest.SpanStub) map[string]string {
	out := map[string]string{}
	for _, kv := range s.Attributes {
		out[string(kv.Key)] = kv.Value.Emit()
	}
	return out
}
