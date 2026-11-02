package errtracking

import (
	"bytes"
	"compress/gzip"
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"

	"github.com/getsentry/sentry-go"
	"github.com/rs/zerolog"
	"go.opentelemetry.io/otel/trace"
)

// receiver is a fake Sentry ingest that keeps every payload it gets.
type receiver struct {
	server   *httptest.Server
	mu       sync.Mutex
	payloads []string
}

func newReceiver(t *testing.T) *receiver {
	t.Helper()

	r := &receiver{}
	r.server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		var reader io.Reader = req.Body
		if req.Header.Get("Content-Encoding") == "gzip" {
			gz, err := gzip.NewReader(req.Body)
			if err != nil {
				t.Error(err)

				return
			}
			defer gz.Close()
			reader = gz
		}

		body, err := io.ReadAll(reader)
		if err != nil {
			t.Error(err)

			return
		}

		r.mu.Lock()
		r.payloads = append(r.payloads, string(body))
		r.mu.Unlock()

		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{}`))
	}))
	t.Cleanup(r.server.Close)

	return r
}

func (r *receiver) dsn() string {
	return "http://test-key@" + strings.TrimPrefix(r.server.URL, "http://") + "/1"
}

func (r *receiver) all() string {
	r.mu.Lock()
	defer r.mu.Unlock()

	return strings.Join(r.payloads, "\n")
}

func TestEventsCarryTheStaticMessageAndNothingPrivate(t *testing.T) {
	previous := sentry.CurrentHub().Client()
	defer sentry.CurrentHub().BindClient(previous)

	rx := newReceiver(t)
	flush, err := Init(Options{
		DSN:         rx.dsn(),
		Environment: "stg",
		Release:     "svc@1.2.3",
		ServiceName: "svc",
		NodeName:    "node-1",
	})
	if err != nil {
		t.Fatal(err)
	}

	sentry.CurrentHub().ConfigureScope(func(scope *sentry.Scope) {
		scope.SetUser(sentry.User{ID: "private-user", Email: "private-email"})
		scope.SetTag("private-tag", "private-value")
		scope.SetContext("private-context", sentry.Context{"token": "private-context-token"})
		scope.AddBreadcrumb(&sentry.Breadcrumb{Message: "private-breadcrumb"}, 10)
	})

	span := trace.NewSpanContext(trace.SpanContextConfig{
		TraceID: trace.TraceID{1}, SpanID: trace.SpanID{2}, TraceFlags: trace.FlagsSampled,
	})
	ctx := trace.ContextWithSpanContext(context.Background(), span)

	var logs bytes.Buffer
	logger := zerolog.New(&logs).Hook(&Hook{})
	logger.Warn().Msg("expected upstream fault")
	logger.Error().Msg("request completed")
	logger.Error().Ctx(ctx).Str("error", "private-token").Msg("API request failed")
	logger.Error().Ctx(ctx).Msg("API request failed") // throttled: one event per minute
	flush()

	got := rx.all()
	wanted := []string{
		"API request failed", span.TraceID().String(), "svc@1.2.3", `"environment":"stg"`,
	}
	for _, want := range wanted {
		if !strings.Contains(got, want) {
			t.Fatalf("event is missing %q: %s", want, got)
		}
	}

	if strings.Count(got, `"message":"API request failed"`) != 1 {
		t.Fatal("the repeated message was not throttled")
	}

	for _, forbidden := range []string{"private-", "expected upstream fault", "request completed"} {
		if strings.Contains(got, forbidden) {
			t.Fatalf("forbidden event content: %s", forbidden)
		}
	}
}

func TestEmptyDSNDisablesReporting(t *testing.T) {
	previous := sentry.CurrentHub().Client()
	defer sentry.CurrentHub().BindClient(previous)

	flush, err := Init(Options{ServiceName: "svc"})
	if err != nil {
		t.Fatal(err)
	}
	defer flush()

	// Nothing to send to; the hook must not panic and must not block.
	logger := zerolog.New(io.Discard).Hook(&Hook{})
	logger.Error().Msg("operation failed")
}

func TestInvalidDSNDoesNotDiscloseItsValue(t *testing.T) {
	_, err := Init(Options{DSN: "private-invalid-dsn"})
	if err == nil || strings.Contains(err.Error(), "private-invalid-dsn") {
		t.Fatal("an invalid DSN must fail without disclosing it")
	}
}

func TestCapturePanicSendsNoPanicValue(t *testing.T) {
	previous := sentry.CurrentHub().Client()
	defer sentry.CurrentHub().BindClient(previous)

	rx := newReceiver(t)
	flush, err := Init(Options{
		DSN: rx.dsn(), Environment: "stg", Release: "svc@1", ServiceName: "svc",
	})
	if err != nil {
		t.Fatal(err)
	}

	func() {
		defer func() {
			if recover() != nil {
				CapturePanic(context.Background())
			}
		}()
		panic("private-panic-value")
	}()
	flush()

	got := rx.all()
	if !strings.Contains(got, "HTTP handler panicked") ||
		strings.Contains(got, "private-panic-value") {
		t.Fatalf("panic event: %s", got)
	}
}
