"""Logging, tracing and error tracking, wired once at startup.

    stop = setup(settings, component="dag")
    try:
        run()
    finally:
        stop()

Logging reads SERVICE_NAME, DEVELOPMENT_ENVIRONMENT|ENV_NAME, NODE_NAME and
LOG_LEVEL; tracing reads the OTEL_* variables; errors read SENTRY_DSN(_FILE).
Each is off, never fatal, when its variables are empty.
"""

from __future__ import annotations

from collections.abc import Callable

from . import service_logging as slog
from .errors import ErrorOptions, setup_errors
from .service_tracing import Tracing


def setup(settings, component: str) -> Callable[[], None]:
    slog.configure_from_env()
    tracing = Tracing.from_env()
    stop_errors = setup_errors(
        ErrorOptions(
            dsn=settings.sentry_dsn.get_secret_value(),
            service_name=settings.service_name,
            environment=settings.env_name,
            release=f"{settings.service_name}@{settings.service_version}",
            node_name=settings.node_name,
            component=component,
        )
    )

    def stop() -> None:
        stop_errors()
        tracing.shutdown()

    return stop
