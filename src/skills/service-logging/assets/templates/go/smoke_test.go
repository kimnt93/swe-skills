package logger

import (
	"context"
	"errors"
	"testing"

	"github.com/rs/zerolog/log"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

// TestSmoke emits the line types a service produces; validate the output with logcheck:
//
//	SERVICE_NAME=ssi-ws-v3 ENV_NAME=local NODE_NAME=docker-host-1 LOG_LEVEL=debug \
//	  go test -count=1 -run TestSmoke -v . \
//	  | python3 scripts/logcheck.py --service ssi-ws-v3 --env local --node docker-host-1 \
//	      --require-trace
func TestSmoke(t *testing.T) {
	if _, err := ConfigureFromEnv(); err != nil {
		t.Skip(err)
	}
	log.Info().
		Uint64("messages_received", 361234).
		Uint64("messages_published", 361233).
		Int("channel_depth", 0).
		Msg("message statistics")
	api := Named("api.request")
	api.Warn().Float64("duration_ms", 1250.5).Str("request_id", "r-1").Msg("slow request")
	log.Debug().Bool("ok", true).Msg("debug line")
	log.Error().
		Err(errors.New("sink write failed")).
		Str("error_type", "*errors.errorString").
		Str("table", "trades").
		Msg("write failed")

	ctx, span := sdktrace.NewTracerProvider().Tracer("smoke").Start(context.Background(), "work")
	defer span.End()
	log.Info().Ctx(ctx).Msg("inside a span")
}
