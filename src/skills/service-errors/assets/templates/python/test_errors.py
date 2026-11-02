"""Error reporting: one event per error line, and nothing private in it."""

from __future__ import annotations

import logging

import pytest
import sentry_sdk
from sentry_sdk.transport import Transport

from service.observability import service_logging as slog
from service.observability.errors import ErrorOptions, setup_errors

DSN = "http://test-key@127.0.0.1:9/1"


class Captured(Transport):
    events: list[dict] = []

    def capture_envelope(self, envelope) -> None:
        event = envelope.get_event()
        if event is not None:
            Captured.events.append(event)


@pytest.fixture(autouse=True)
def reset():
    Captured.events = []
    yield
    slog.set_error_hook(None)


def start(**overrides):
    options = ErrorOptions(
        **{
            "dsn": DSN,
            "service_name": "svc",
            "environment": "stg",
            "release": "svc@1.2.3",
            "node_name": "node-1",
            "component": "api",
            "trace_ids": lambda: ("a" * 32, "b" * 16),
            **overrides,
        }
    )
    return setup_errors(options, transport=Captured)


def test_no_dsn_sends_nothing():
    stop = setup_errors(
        ErrorOptions(
            dsn=None, service_name="svc", environment="stg", release="svc@1"
        )
    )
    slog.configure("svc", environment="stg")
    slog.get_logger("app").error("operation failed")
    stop()
    assert Captured.events == []


def test_unified_logger_error_is_one_event_with_the_identity():
    slog.configure("svc", environment="stg")
    stop = start()
    private = "/".join(["", "secret", "path"])  # not literal in the source
    try:
        raise FileNotFoundError(2, private)
    except FileNotFoundError as exc:
        slog.get_logger("app").error("task failed", exc, submission="s-1")
    stop()
    (event,) = Captured.events
    assert event["environment"] == "stg"
    assert event["release"] == "svc@1.2.3"
    assert event["server_name"] == "node-1"
    assert event["tags"] == {
        "service_name": "svc",
        "component": "api",
        "logger": "app",
        "trace_id": "a" * 32,
        "span_id": "b" * 16,
    }
    value = event["exception"]["values"][0]
    assert value["type"] == "FileNotFoundError"
    assert value["value"] == ""
    assert "/secret/path" not in str(event)
    frames = value["stacktrace"]["frames"]
    assert all("vars" not in frame for frame in frames)


def test_stdlib_error_is_reported_and_nothing_private_travels():
    slog.configure("svc", environment="stg")
    stop = start()
    sentry_sdk.set_user({"id": "private-user"})
    sentry_sdk.set_tag("private-tag", "private-value")
    sentry_sdk.set_context("private", {"token": "private-token"})
    logging.getLogger("service.api").error("request failed")
    stop()
    (event,) = Captured.events
    text = str(event)
    assert "request failed" in text
    for private in ("private-user", "private-value", "private-token"):
        assert private not in text
    for key in ("request", "user", "breadcrumbs", "contexts", "extra"):
        assert key not in event


def test_warnings_and_exporter_noise_are_not_reported():
    slog.configure("svc", environment="stg")
    stop = start()
    slog.get_logger("app").warn("upstream slow")
    logging.getLogger("service.api").warning("retrying")
    logging.getLogger("opentelemetry.exporter.otlp").error("Failed to export")
    stop()
    assert Captured.events == []


def test_exception_text_is_opt_in():
    slog.configure("svc", environment="stg")
    stop = start(include_exception_text=True)
    try:
        raise ValueError("bad value 42")
    except ValueError as exc:
        slog.get_logger("app").error("parse failed", exc)
    stop()
    assert (
        Captured.events[0]["exception"]["values"][0]["value"] == "bad value 42"
    )
