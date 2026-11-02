# Go (zerolog, Fiber v3)

Reference: `trading-simulator` (`internal/errtracking`, wired from `internal/logger` and `bootstrap`). Template:
`assets/templates/go/errtracking.go` with `errtracking_test.go`, copied to `internal/errtracking/`.

```text
internal/errtracking/errtracking.go   Options, Init, Hook (zerolog.Hook), CapturePanic
internal/config/config.go             SentryDSN (OptSecret: SENTRY_DSN or SENTRY_DSN_FILE)
internal/logger/logger.go             AddHook(h zerolog.Hook)  (in the go-code and service-logging templates)
cmd/api/main.go                       Init after the logger, AddHook, defer flush
```

## Wiring

1. `go get github.com/getsentry/sentry-go`.
2. Config: `SentryDSN string` read with `l.OptSecret("SENTRY_DSN")` (optional: empty turns reporting off).
3. In `run()`, after `logger.ConfigureFromEnv()`:

   ```go
   flushErrors, err := errtracking.Init(errtracking.Options{
       DSN:         cfg.SentryDSN,
       Environment: cfg.Environment,
       Release:     cfg.ServiceName + "@" + cfg.ServiceVersion,
       ServiceName: cfg.ServiceName,
       NodeName:    cfg.NodeName,
   })
   if err != nil {
       return err // "SENTRY_DSN is invalid": the value is never printed
   }
   defer flushErrors()

   // Every error-level line of every logger becomes one event.
   logger.AddHook(&errtracking.Hook{})
   ```

4. Panics: in the HTTP recovery boundary call `errtracking.CapturePanic(c.Context())` (Fiber: inside the
   `recover` middleware's `StackTraceHandler`, or your own `defer`). It sends a fixed message and the stack, not the value.
5. `.env.example`: copy `assets/sentry.env.example`; Compose: `assets/compose.sentry.yaml`.

## Behaviour to keep

- The hook only reads the level and the **message**. Fields on the event (`.Err(err)`, `.Str(...)`) are never read, so
  `log.Error().Err(err).Str("order", id).Msg("order failed")` sends only `order failed` (plus trace ids from `.Ctx(ctx)`).
  Pass the request context with `.Ctx(ctx)` so `trace_id` and `span_id` are attached.
- `skipped` in `errtracking.go` lists messages that are not failures (`request completed`, the RequestLog line). Add a noisy
  message there on purpose, not to hide a real failure.
- `SendDefaultPII`, breadcrumbs, tracing and the telemetry buffer are off or default-off; `scrub` deletes request, user,
  breadcrumbs, contexts, attachments and every tag outside `service_name`, `trace_id`, `span_id`.
- The throttle is per `Hook` value: install **one** hook with `AddHook`. `CapturePanic` has its own shared hook, so a panic
  loop is one event a minute, like any other repeated error.

## Tests (shipped)

`errtracking_test.go` starts a fake ingest (`httptest`) and proves: only the error line is reported, once; the release,
environment and trace id are present; private scope data (user, tag, context, breadcrumb) never leaves; an empty DSN
disables reporting; an invalid DSN is not echoed; a panic sends no panic value. Run `go test ./internal/errtracking/`.
