// Package errtracking reports bounded operational errors to Sentry or GlitchTip (the Sentry
// protocol). Copy it to internal/errtracking/ and wire it once (see references/go.md):
//
//	flush, err := errtracking.Init(errtracking.Options{DSN: cfg.SentryDSN, ...})
//	defer flush()
//	zerolog.New(w).Hook(&errtracking.Hook{})           // every error-level line becomes one event
//	errtracking.CapturePanic(c.Context())               // at the HTTP recovery boundary
//
// An event carries the static log message, a stack, the environment, the release and the
// service_name / trace_id / span_id tags. It never carries a request, a user, breadcrumbs,
// contexts, attachments, or the error text of the log line (the detail stays in the local logs).
// Traces belong to OpenTelemetry, not to Sentry.
package errtracking

import (
	"context"
	"errors"
	"sync"
	"time"

	"github.com/getsentry/sentry-go"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	"go.opentelemetry.io/otel/trace"
)

const (
	flushTimeout = 5 * time.Second

	// One event per message per minute per process; local logs keep every occurrence.
	throttleWindow = time.Minute

	tagService = "service_name"
	tagTrace   = "trace_id"
	tagSpan    = "span_id"
)

// Options configures Init. An empty DSN disables reporting.
type Options struct {
	DSN         string // SENTRY_DSN, read from a secret file in Swarm; never logged
	Environment string // ENV_NAME: stg, prod, ...
	Release     string // "<service_name>@<SERVICE_VERSION>"
	ServiceName string // SERVICE_NAME
	NodeName    string // NODE_NAME, shown as the server name
}

// errInvalidDSN never contains the DSN: it holds the ingest key.
var errInvalidDSN = errors.New("SENTRY_DSN is invalid")

// skipped lists error-level messages that are not operational failures: the request summary line
// and noisy retries. Add a message here on purpose.
var skipped = map[string]bool{
	"request completed": true,
}

// Init binds a process-local client to the current hub and returns the function that flushes and
// closes it at shutdown. Call it before the logger starts using Hook.
func Init(o Options) (func(), error) {
	client, err := sentry.NewClient(sentry.ClientOptions{
		Dsn:              o.DSN,
		Environment:      o.Environment,
		Release:          o.Release,
		ServerName:       o.NodeName,
		AttachStacktrace: true,
		EnableTracing:    false, // OpenTelemetry owns traces; PII stays off (the default)

		// The JSON envelope transport is the one GlitchTip accepts.
		DisableTelemetryBuffer: true,
		BeforeSend:             scrub,
	})
	if err != nil {
		return nil, errInvalidDSN
	}

	hub := sentry.CurrentHub()
	hub.BindClient(client)
	hub.ConfigureScope(func(scope *sentry.Scope) {
		scope.Clear()
		scope.SetTag(tagService, o.ServiceName)
	})

	return func() {
		if !client.Flush(flushTimeout) {
			log.Warn().Msg("error reporting shutdown did not flush all events")
		}
		client.Close()
	}, nil
}

// scrub removes everything except the static message, the stack and three tags.
func scrub(event *sentry.Event, _ *sentry.EventHint) *sentry.Event {
	event.Request = nil
	event.User = sentry.User{}
	event.Breadcrumbs = nil
	event.Contexts = nil
	event.Attachments = nil

	for tag := range event.Tags {
		if tag != tagService && tag != tagTrace && tag != tagSpan {
			delete(event.Tags, tag)
		}
	}

	return event
}

// Hook reports error-level and fatal log lines. Warnings are never reported: expected faults,
// reconnects and retries belong in logs and metrics.
type Hook struct {
	mu   sync.Mutex
	last map[string]time.Time
}

// Run implements zerolog.Hook.
func (h *Hook) Run(event *zerolog.Event, level zerolog.Level, message string) {
	if level != zerolog.ErrorLevel && level != zerolog.FatalLevel {
		return
	}

	if skipped[message] || h.throttled(message) {
		return
	}

	hub := sentry.CurrentHub().Clone()
	scope := hub.Scope()

	if span := trace.SpanContextFromContext(event.GetCtx()); span.IsValid() {
		scope.SetTag(tagTrace, span.TraceID().String())
		scope.SetTag(tagSpan, span.SpanID().String())
	}

	scope.SetLevel(sentry.LevelError)
	hub.CaptureMessage(message)
}

// throttled reports whether this message was already sent within the window.
func (h *Hook) throttled(message string) bool {
	h.mu.Lock()
	defer h.mu.Unlock()

	if h.last == nil {
		h.last = make(map[string]time.Time)
	}

	now := time.Now()
	if now.Sub(h.last[message]) < throttleWindow {
		return true
	}

	h.last[message] = now

	return false
}

// panicHook is shared so a panic loop is throttled like any other repeated error.
var panicHook = &Hook{}

// CapturePanic reports a fixed message with a stack at the recovery boundary. The panic value is
// not sent: it can contain business data or a secret.
func CapturePanic(ctx context.Context) {
	logger := zerolog.New(nil).Hook(panicHook)
	logger.Error().Ctx(ctx).Msg("HTTP handler panicked")
}
