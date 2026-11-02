# Go (zerolog)

Template: `assets/templates/go/logger.go` (`package logger`; copy to `internal/logger/`). Smoke
test: `smoke_test.go`. Library: [rs/zerolog](https://github.com/rs/zerolog). Tested with Go 1.26,
zerolog 1.35, otel-go 1.47.

```bash
go get github.com/rs/zerolog go.opentelemetry.io/otel/trace
go get go.opentelemetry.io/otel/sdk   # only for the smoke test
```

## Use

```go
if _, err := logger.ConfigureFromEnv(); err != nil { // SERVICE_NAME, DEVELOPMENT_ENVIRONMENT|ENV_NAME, NODE_NAME, LOG_LEVEL
    panic(err)
}
log.Info().Uint64("messages_received", n).Int("channel_depth", len(queue)).Msg("message statistics")
api := logger.Named("api.request")                  // logger = api.request
api.Warn().Ctx(ctx).Float64("duration_ms", 1250.5).Msg("slow request")   // + trace_id, span_id
log.Error().Err(err).Str("error_type", fmt.Sprintf("%T", err)).Msg("sink write failed")
```

`ConfigureFromEnv` installs the logger as zerolog's global (`log.Logger`, `logger=root`), so existing
`github.com/rs/zerolog/log` call sites keep working; pass loggers into components with
`logger.Named("kafka.producer")`.

Docker: set `NODE_NAME` (Swarm `{{.Node.Hostname}}`); the template falls back to the hostname.

## What the template configures

- field names `time`, `level`, `message`, `caller`, and `ErrorFieldName = "error"`;
- `time` as UTC with a fixed `.000000000` layout (zerolog's `RFC3339Nano` trims zeros);
- `caller` as `<module name>/<path in the module>:<line>`. With `-trimpath` the compiler already
  records the module path; without it the template makes the path relative to the `go.mod`
  directory found from the working directory. Build deployed binaries with `-trimpath`;
  a plain binary started outside the module falls back to the last two path elements;
- a hook adding `trace_id`/`span_id` when the event has a context with a valid span.

## Gotchas

- Trace ids need the context on the event: `.Ctx(ctx)` (zerolog 1.30+). Without it no ids are written.
- Never log `Fatal()` casually: it calls `os.Exit`. Return the error and log `error`.
- `error_type` is optional in Go; add it with `%T` when the type helps.
- `Named` returns a new logger each call: create it once per component, not per message.
- Tests: use `zerolog.Nop()` or a buffer as `Options.Output`; do not read global state.

## Verify

```bash
SERVICE_NAME=ssi-ws-v3 ENV_NAME=local NODE_NAME=docker-host-1 LOG_LEVEL=debug go test -count=1 -run TestSmoke -v ./internal/logger \
  | python3 scripts/logcheck.py --service ssi-ws-v3 --env local --node docker-host-1 --require-trace
```
