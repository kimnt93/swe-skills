"""Errors to Sentry or GlitchTip through the Sentry SDK (service-errors skill).

Every `error` or `fatal` log line of the process becomes one event. The code
reports a failure once with `log.error(...)`; an event carries the log message,
the exception type and its stack, the environment, the release
(`<service_name>@<version>`), the node as server name, and the tags
`service_name`, `component`, `logger`, `trace_id` and `span_id`.

It never carries request data, a user, breadcrumbs, local variables (a frame's
locals can hold submitted data), contexts, or the exception text (it can hold a
DSN, a query or user input; the text stays in the local log line).
OpenTelemetry owns traces: the SDK's tracing and automatic integrations are
off.

Off unless a DSN is given. A Sentry outage never breaks a request: the SDK
sends from a bounded background queue.

Wire it once, after logging is configured:

    stop = setup_errors(
        ErrorOptions(
            dsn=settings.sentry_dsn,  # str | None, from SENTRY_DSN(_FILE)
            service_name=settings.service_name,
            environment=settings.env_name,
            release=f"{settings.service_name}@{settings.service_version}",
            node_name=settings.node_name,
            component="api",
        )
    )
    ...
    stop()  # at shutdown: flushes and closes
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import service_logging

# Loggers whose errors are not application failures: the SDK itself and the
# telemetry exporters (a collector that is down must not fill Sentry).
SKIPPED_LOGGERS = ("sentry_sdk", "opentelemetry")

ALLOWED_TAGS = {"service_name", "component", "logger", "trace_id", "span_id"}
DROPPED_KEYS = (
    "request",
    "user",
    "breadcrumbs",
    "contexts",
    "extra",
    "modules",
)

TraceIds = Callable[[], tuple[str, str]]


def otel_trace_ids() -> tuple[str, str]:
    """The trace and span id of the current OpenTelemetry span, or ("", "")."""
    try:
        from opentelemetry import trace
    except ImportError:
        return "", ""
    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return "", ""
    return f"{context.trace_id:032x}", f"{context.span_id:016x}"


@dataclass(frozen=True)
class ErrorOptions:
    dsn: str | None  # blank or None turns reporting off
    service_name: str
    environment: str
    release: str  # "<service_name>@<SERVICE_VERSION>"
    node_name: str = ""
    component: str = ""  # api, worker, ...
    include_exception_text: bool = False
    trace_ids: TraceIds = otel_trace_ids


def setup_errors(
    options: ErrorOptions, *, transport: Any = None
) -> Callable[[], None]:
    """Start error reporting for this process; returns the function that
    flushes and stops it. A missing or blank DSN does nothing.
    """
    dsn = (options.dsn or "").strip()
    if not dsn:
        return lambda: None

    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration

    before_send = _make_before_send(
        options.include_exception_text, options.trace_ids
    )
    sentry_sdk.init(
        dsn=dsn,
        environment=options.environment,
        release=options.release,
        server_name=options.node_name or None,
        default_integrations=False,
        integrations=[
            LoggingIntegration(level=None, event_level=logging.ERROR)
        ],
        # send_default_pii stays at its default, False
        include_local_variables=False,
        max_breadcrumbs=0,
        traces_sample_rate=None,
        before_send=before_send,
        shutdown_timeout=2,
        transport=transport,
    )
    scope = sentry_sdk.get_global_scope()
    scope.set_tag("service_name", options.service_name)
    if options.component:
        scope.set_tag("component", options.component)
    client = sentry_sdk.get_client()

    def report(name: str, message: str, exc: BaseException | None) -> None:
        # The unified Logger does not go through `logging`, so it reports here.
        with sentry_sdk.new_scope() as local:
            local.set_tag("logger", name)
            local.fingerprint = [name, message]
            if exc is not None:
                local.capture_exception(exc)
            else:
                local.capture_message(message, level="error")

    service_logging.set_error_hook(report)

    def stop() -> None:
        service_logging.set_error_hook(None)
        client.close(timeout=2)
        if sentry_sdk.get_client() is client:
            scope.set_client(None)

    return stop


def _make_before_send(
    include_exception_text: bool, trace_ids: TraceIds
) -> Callable[[dict[str, Any], dict[str, Any]], dict[str, Any] | None]:
    def before_send(
        event: dict[str, Any], hint: dict[str, Any]
    ) -> dict[str, Any] | None:
        if (event.get("logger") or "").startswith(SKIPPED_LOGGERS):
            return None
        for key in DROPPED_KEYS:
            event.pop(key, None)
        tags = event.get("tags")
        if isinstance(tags, dict):
            event["tags"] = {
                k: v for k, v in tags.items() if k in ALLOWED_TAGS
            }
        if event.get("logger"):
            event.setdefault("tags", {})["logger"] = event["logger"]
        trace_id, span_id = trace_ids()  # the thread that logged the failure
        if trace_id:
            event.setdefault("tags", {})["trace_id"] = trace_id
            event["tags"]["span_id"] = span_id
        _scrub_exceptions(event, include_exception_text)
        return event

    return before_send


def _scrub_exceptions(event: dict[str, Any], include_text: bool) -> None:
    for item in (event.get("exception") or {}).get("values") or []:
        if not include_text:
            item["value"] = ""
        for frame in (item.get("stacktrace") or {}).get("frames") or []:
            frame.pop("vars", None)
