# Python (jlogger)

Template: `assets/templates/python/service_logging.py` (copy into the service). Smoke test:
`assets/templates/python/smoke.py`. Library: [kimnt93/jlogger](https://github.com/kimnt93/jlogger).

```toml
# pyproject.toml (uv)
dependencies = ["jlogger", "opentelemetry-api"]    # opentelemetry-api only for trace ids
[tool.uv.sources]
jlogger = { git = "https://github.com/kimnt93/jlogger.git" }
```

Tested with Python 3.12 and jlogger 0.1.0. jlogger ships a prebuilt extension (no Rust toolchain).

## Use

```python
import service_logging as slog

slog.configure_from_env()      # SERVICE_NAME, DEVELOPMENT_ENVIRONMENT|ENV_NAME, NODE_NAME, LOG_LEVEL
log = slog.get_logger()                         # logger = "root"
log.info("message statistics", messages_received=361234, channel_depth=0)
req = slog.get_logger("api.request").bind(request_id=rid)   # bound fields on every line
req.warn("slow request", duration_ms=1250.5)
try:
    write(batch)
except Exception as exc:
    log.exception("sink write failed", exc, table="trades")  # error, error_type, stack
```

Methods: `debug`, `info`, `warn`, `error(msg, exc=None, **f)`, `fatal(msg, exc=None, **f)`,
`exception(msg, exc=None, **f)`, `bind(**f)`. Keyword arguments are the custom fields.

Standard `logging` (frameworks, libraries, Pathway, uvicorn) is bridged automatically:
`logging.getLogger(__name__).warning("x", extra={"fields": {"attempt": 2}})` becomes a unified
line with `logger = __name__`. `configure(..., bridge_stdlib=False)` turns the bridge off.

Docker: set `NODE_NAME` (Swarm `{{.Node.Hostname}}`); the template falls back to the hostname.
Pass `caller_root=Path(...)` to `configure` if the working directory is not inside the project.

## Why an adapter on top of jlogger

jlogger writes the JSON with a Rust encoder, but its defaults miss the format: no `caller`, its
`RFC3339` option is a local timestamp without a zone, and it names warnings `warning`. jlogger
lets `with_values` replace `time`, `level`, `logger` and `message` in place (no duplicate keys),
which the adapter uses to write the unified values. Disabled levels return before any work.

## Gotchas

- Call `configure_from_env()` once, early, before other modules create loggers.
- Custom field names that collide with core fields become `field_<name>`.
- `caller` for bridged library records is the library's logging call site
  (`pathway/...`), trimmed after `site-packages/`.
- Do not use `print` for diagnostics in services; it breaks the one-JSON-per-line rule.

## Verify

```bash
cd assets/templates/python
SERVICE_NAME=ssi-ws-v3 ENV_NAME=local NODE_NAME=docker-host-1 LOG_LEVEL=debug python smoke.py \
  | python3 ../../../scripts/logcheck.py --service ssi-ws-v3 --env local --node docker-host-1 --require-trace
```
