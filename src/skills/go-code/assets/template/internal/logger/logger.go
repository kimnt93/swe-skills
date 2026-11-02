// Package logger configures zerolog for the unified service log format (see
// references/log-format.md). Copy this file into internal/logger/ and call once at startup:
//
//	// Reads SERVICE_NAME, DEVELOPMENT_ENVIRONMENT|ENV_NAME, NODE_NAME, LOG_LEVEL.
//	if _, err := logger.ConfigureFromEnv(); err != nil {
//		panic(err)
//	}
//
//	// Global logger, logger=root.
//	log.Info().Uint64("messages_received", n).Msg("message statistics")
//
//	// Named logger, logger=api.request; adds trace_id and span_id from ctx.
//	api := logger.Named("api.request")
//	api.Warn().Ctx(ctx).Int("status_code", 503).Msg("upstream unavailable")
//
// Every line has level, development_environment, service_name, node_name, logger, time (UTC
// RFC 3339, exactly 9 fractional digits), caller (<root>/<relative path>:<line>) and message,
// plus trace_id/span_id when the event carries a context with an active OpenTelemetry span.
package logger

import (
	"fmt"
	"io"
	"os"
	"path"
	"runtime/debug"
	"strings"
	"time"

	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	"go.opentelemetry.io/otel/trace"
)

// Options configures Configure. Service is required.
type Options struct {
	Service     string    // SERVICE_NAME
	Environment string    // DEVELOPMENT_ENVIRONMENT or ENV_NAME; default "local"
	Node        string    // NODE_NAME; default the hostname (a container id in a bridge network)
	Level       string    // LOG_LEVEL; default "info"
	Output      io.Writer // default os.Stdout
	Root        string    // caller root name; default the last element of the Go module path
}

var (
	base     zerolog.Logger // identity fields, no logger field yet
	rootName string
	rootDir  string // directory holding go.mod, for builds without -trimpath
)

// ConfigureFromEnv reads SERVICE_NAME (required), DEVELOPMENT_ENVIRONMENT else ENV_NAME else
// "local", NODE_NAME (in Docker set it to the host name) and LOG_LEVEL.
func ConfigureFromEnv() (zerolog.Logger, error) {
	service := os.Getenv("SERVICE_NAME")
	if service == "" {
		return zerolog.Logger{}, fmt.Errorf("SERVICE_NAME is required (the service name)")
	}

	environment := firstNonEmpty(
		os.Getenv("DEVELOPMENT_ENVIRONMENT"),
		os.Getenv("ENV_NAME"),
		"local",
	)

	return Configure(Options{
		Service:     service,
		Environment: environment,
		Node:        os.Getenv("NODE_NAME"),
		Level:       os.Getenv("LOG_LEVEL"),
	}), nil
}

// Configure installs the logger as zerolog's global (log.Logger) and returns it.
func Configure(o Options) zerolog.Logger {
	zerolog.TimestampFieldName = "time"
	zerolog.LevelFieldName = "level"
	zerolog.MessageFieldName = "message"
	zerolog.ErrorFieldName = "error"
	zerolog.CallerFieldName = "caller"
	// Fixed width: RFC3339Nano trims trailing zeros, which breaks sorting and parsing.
	zerolog.TimeFieldFormat = "2006-01-02T15:04:05.000000000Z07:00"
	zerolog.TimestampFunc = func() time.Time {
		return time.Now().UTC()
	}
	zerolog.CallerMarshalFunc = marshalCaller
	level, err := zerolog.ParseLevel(strings.ToLower(firstNonEmpty(o.Level, "info")))
	if err != nil {
		level = zerolog.InfoLevel
	}
	zerolog.SetGlobalLevel(level)
	if o.Node == "" {
		o.Node, _ = os.Hostname()
	}
	if o.Output == nil {
		o.Output = os.Stdout
	}
	rootDir = moduleRoot()
	rootName = o.Root
	if rootName == "" {
		if info, ok := debug.ReadBuildInfo(); ok && info.Main.Path != "" {
			rootName = path.Base(info.Main.Path)
		} else if rootDir != "" {
			rootName = path.Base(rootDir)
		}
	}
	// Hooks run in order at write time: trace ids first, then time and caller.
	base = zerolog.New(o.Output).Level(level).Hook(traceHook{}).With().
		Str("development_environment", firstNonEmpty(o.Environment, "local")).
		Str("service_name", o.Service).
		Str("node_name", o.Node).Logger()
	log.Logger = Named("root")
	return log.Logger
}

// AddHook runs h for every line written by the root logger and by every logger from Named, after
// Configure. Error tracking uses it (service-errors skill): AddHook(&errtracking.Hook{}).
func AddHook(h zerolog.Hook) {
	base = base.Hook(h)
	log.Logger = Named("root")
}

// Named returns a logger with logger=name (the Go equivalent of a module-named logger).
func Named(name string) zerolog.Logger {
	return base.With().Str("logger", name).Timestamp().Caller().Logger()
}

type traceHook struct{}

// Run adds trace_id and span_id when the event has a context (event.Ctx(ctx)) with a valid span.
func (traceHook) Run(e *zerolog.Event, _ zerolog.Level, _ string) {
	if ctx := e.GetCtx(); ctx != nil {
		if sc := trace.SpanContextFromContext(ctx); sc.IsValid() {
			e.Str("trace_id", sc.TraceID().String()).Str("span_id", sc.SpanID().String())
		}
	}
}

// moduleRoot finds the directory holding go.mod by walking up from the working directory.
func moduleRoot() string {
	dir, err := os.Getwd()
	for err == nil && dir != "/" && dir != "." {
		if _, statErr := os.Stat(dir + "/go.mod"); statErr == nil {
			return dir
		}
		dir = path.Dir(dir)
	}
	return ""
}

// marshalCaller prints <root>/<path relative to the module root>:<line>. With -trimpath the
// compiler already records <module path>/<file>; without it the absolute path is made
// relative to the go.mod directory, so both builds print the same value.
func marshalCaller(_ uintptr, file string, line int) string {
	root := rootName

	info, hasBuildInfo := debug.ReadBuildInfo()
	if hasBuildInfo && info.Main.Path != "" && strings.HasPrefix(file, info.Main.Path+"/") {
		relative := strings.TrimPrefix(file, info.Main.Path+"/")

		return fmt.Sprintf("%s/%s:%d", root, relative, line)
	}

	if rootDir != "" && strings.HasPrefix(file, rootDir+"/") {
		relative := strings.TrimPrefix(file, rootDir+"/")

		return fmt.Sprintf("%s/%s:%d", root, relative, line)
	}

	// A dependency.
	if i := strings.Index(file, "/pkg/mod/"); i >= 0 {
		return fmt.Sprintf("%s:%d", file[i+len("/pkg/mod/"):], line)
	}

	return fmt.Sprintf("%s/%s:%d", path.Base(path.Dir(file)), path.Base(file), line)
}

func firstNonEmpty(values ...string) string {
	for _, v := range values {
		if v != "" {
			return v
		}
	}
	return ""
}
