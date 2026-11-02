"""Smoke test: emit the line types a service produces, then validate them.

    SERVICE_NAME=ssi-ws-v3 ENV_NAME=local NODE_NAME=docker-host-1 \\
      LOG_LEVEL=debug python smoke.py \\
      | python3 ../../../scripts/logcheck.py --service ssi-ws-v3 \\
          --env local --node docker-host-1 --require-trace
"""

import logging

import service_logging as slog

slog.configure_from_env()
log = slog.get_logger()
log.info(
    "message statistics",
    messages_received=361234,
    messages_published=361233,
    channel_depth=0,
)
slog.get_logger("api.request").bind(request_id="r-1").warn(
    "slow request", duration_ms=1250.5
)
log.debug("custom field named time", time=5, ok=True)
try:
    1 / 0  # noqa: B018 - raises on purpose
except ZeroDivisionError as error:
    log.exception("division failed", error, divisor=0)

logging.getLogger("some.library").warning(
    "library warning", extra={"fields": {"attempt": 2}}
)

try:
    from opentelemetry.sdk.trace import TracerProvider

    with TracerProvider().get_tracer("smoke").start_as_current_span("work"):
        log.info("inside a span")
except ImportError:
    pass
