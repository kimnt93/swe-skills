# Python (Litestar, stdlib `logging`, the unified logger)

Reference: `vibe-alpha/alpha-server` (`observability/errors.py`, `setup_errors` called from `observability.setup`).
Template: `assets/templates/python/errors.py` with `test_errors.py`, copied to `src/service/observability/` and `tests/`.

```text
observability/errors.py               ErrorOptions, setup_errors, otel_trace_ids
observability/service_logging.py      set_error_hook(hook)  (in the py-code and service-logging templates)
settings/__init__.py                  sentry_dsn: Secret | None   (SENTRY_DSN or SENTRY_DSN_FILE)
cli.py                                setup_errors(...) after slog.configure_from_env(); stop() in finally
```

## Wiring

1. Dependency: `"sentry-sdk>=2.20"` in `pyproject.toml` (nothing is sent without a DSN).
2. Settings:

   ```python
   # Sentry/GlitchTip ingest URL: SENTRY_DSN or SENTRY_DSN_FILE; unset turns error reporting off.
   sentry_dsn: Secret | None = Field(None, validation_alias="SENTRY_DSN")
   ```

   `EnvSettings` already maps `SENTRY_DSN_FILE` to a `SecretStr` field.
3. In the entrypoint, after logging is configured:

   ```python
   from .observability.errors import ErrorOptions, setup_errors

   dsn = settings.sentry_dsn.get_secret_value() if settings.sentry_dsn else None
   stop_errors = setup_errors(
       ErrorOptions(
           dsn=dsn,
           service_name=settings.service_name,
           environment=settings.env_name,
           release=f"{settings.service_name}@{settings.service_version}",
           node_name=settings.node_name,
           component="api",            # "worker" in the worker process
       )
   )
   try:
       uvicorn.run(...)
   finally:
       stop_errors()                    # flushes within 2 s, then closes
   ```

4. Every process that should report (API, Celery worker, CLI job) calls `setup_errors` itself with its own `component`;
   a forked worker calls it **after** the fork. The sandbox child never does.

## How lines reach Sentry

- **Standard `logging`** records (libraries, Litestar, `logging.getLogger(...)`) at `ERROR` and above: the SDK's
  `LoggingIntegration(event_level=ERROR)`. Automatic integrations stay off, so no request data is collected.
- **The unified `Logger`** (`slog.get_logger("app").error("task failed", exc)`) does not use `logging`, so
  `setup_errors` registers `service_logging.set_error_hook`; it reports the same line once. The exception, when given, travels
  as type + stack (no text, no locals); the logger name becomes the `logger` tag and, with the message, the fingerprint.

## Behaviour to keep

- `before_send` drops `request`, `user`, `breadcrumbs`, `contexts`, `extra`, `modules`, every tag outside the allowlist,
  stack-frame `vars`, and the exception **text** (`ErrorOptions.include_exception_text=True` opts in per service).
- `SKIPPED_LOGGERS` (`sentry_sdk`, `opentelemetry`) keep a broken telemetry pipeline from filling the project.
  Add `celery.app.trace` when Celery reports the same failure as your own `task failed` line.
- `trace_id`/`span_id` come from the current OpenTelemetry span in the thread that logged (`otel_trace_ids`); pass
  your own `trace_ids` function when the project has its own helper.
- `send_default_pii`, local variables, breadcrumbs and tracing are off (the SDK default or explicitly).

## Tests (shipped)

`test_errors.py` uses a capturing `Transport` and proves: no DSN sends nothing; a unified-logger error is one event with
environment, release, server name, tags and no exception text or `vars`; a stdlib error is reported and no scope data
(user, tag, context) leaves; warnings and exporter noise are not reported; exception text is opt-in.
`test_settings.py` gains a test that `SENTRY_DSN_FILE` is read and that the DSN is optional.
