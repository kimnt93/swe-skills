"""Unified service logging on jlogger (https://github.com/kimnt93/jlogger).

Copy this file into the service. One call at startup, then log anywhere:

    import service_logging as slog

    # Reads SERVICE_NAME, DEVELOPMENT_ENVIRONMENT|ENV_NAME, NODE_NAME and
    # LOG_LEVEL.
    slog.configure_from_env()

    log = slog.get_logger()  # logger = "root"
    api = slog.get_logger("api.request")  # a named logger

    log.info("message statistics", messages_received=361234, channel_depth=0)
    log.exception("sink write failed", exc, table="trades")

Every line has level, development_environment, service_name, node_name,
logger, time (UTC RFC 3339, 9 fractional digits), caller
(<root>/<relative path>:<line>) and message, plus trace_id/span_id inside an
active OpenTelemetry span, plus your flat custom fields.
jlogger's own time/level/caller are replaced: its RFC3339 option has no
timezone and no caller, and it names warnings "warning". Standard `logging`
records (libraries, frameworks) are bridged into the same format; pass fields
with extra={"fields": {...}}.
"""

from __future__ import annotations

import logging
import math
import os
import socket
import sys
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any, TextIO

import jlogger

try:  # trace correlation is optional
    from opentelemetry import trace as _otel_trace
except ImportError:  # pragma: no cover
    _otel_trace = None

# Names a custom field may not use; a colliding key is written as field_<key>.
RESERVED = frozenset(
    {
        "level",
        "development_environment",
        "service_name",
        "node_name",
        "logger",
        "time",
        "caller",
        "message",
        "trace_id",
        "span_id",
    }
)
MAX_TEXT = 2000
_RANK = {"debug": 10, "info": 20, "warn": 30, "error": 40, "fatal": 50}
_JLOGGER = {
    "debug": "debug",
    "info": "info",
    "warn": "warning",
    "error": "error",
    "fatal": "critical",
}
_STDLIB = {
    logging.DEBUG: "debug",
    logging.INFO: "info",
    logging.WARNING: "warn",
    logging.ERROR: "error",
    logging.CRITICAL: "fatal",
}

_identity: dict[str, str] = {}
_threshold = _RANK["info"]
_root: Path = Path.cwd()
_caller_cache: dict[str, str] = {}


def configure(
    service_name: str,
    *,
    environment: str,
    node_name: str | None = None,
    level: str = "info",
    stream: TextIO | None = None,
    caller_root: Path | None = None,
    bridge_stdlib: bool = True,
) -> None:
    """Set the identity fields, level, output (default stdout) and caller root.

    `caller_root` is the project directory; callers print as
    `<its name>/<relative path>`. Default: the nearest ancestor of the working
    directory holding pyproject.toml or .git.
    """
    global _threshold, _root
    _identity.update(
        development_environment=environment,
        service_name=service_name,
        node_name=node_name or socket.gethostname(),
    )
    _threshold = _RANK.get(_normalize(level), _RANK["info"])
    _root = (caller_root or _find_root()).resolve()
    _caller_cache.clear()
    jlogger.set_output(stream or sys.stdout)
    # Filtering happens here, before any work is done.
    jlogger.set_level("debug")
    if bridge_stdlib:
        root = logging.getLogger()
        root.handlers[:] = [_StdlibBridge()]
        root.setLevel(logging.DEBUG)
        logging.captureWarnings(True)


def configure_from_env(**overrides: Any) -> None:
    """configure() from the environment, the same variables in every language:

    SERVICE_NAME (required) -> service_name; DEVELOPMENT_ENVIRONMENT, else
    ENV_NAME, else "local" -> development_environment; NODE_NAME -> node_name
    (in Docker set it to the host's name, see references/log-format.md; unset
    falls back to the hostname, which in a bridge-network container is the
    container id); LOG_LEVEL (default info).
    """
    service = os.environ.get("SERVICE_NAME")
    if not service:
        raise RuntimeError(
            "SERVICE_NAME is required (the service name, e.g. feed-ws)"
        )
    configure(
        service,
        environment=os.environ.get("DEVELOPMENT_ENVIRONMENT")
        or os.environ.get("ENV_NAME")
        or "local",
        node_name=os.environ.get("NODE_NAME") or None,
        level=os.environ.get("LOG_LEVEL", "info"),
        **overrides,
    )


_error_hook: Callable[[str, str, BaseException | None], None] | None = None


def set_error_hook(
    hook: Callable[[str, str, BaseException | None], None] | None,
) -> None:
    """Call `hook(logger_name, message, exc)` for every error or fatal line the
    unified `Logger` writes (error tracking, service-errors skill). Standard
    `logging` records reach error tracking through the SDK's logging
    integration instead, so a line is never reported twice. `None` removes it.
    """
    global _error_hook
    _error_hook = hook


def get_logger(name: str = "root") -> Logger:
    return Logger(name, {})


def _normalize(level: str) -> str:
    level = level.lower()
    return {"warning": "warn", "critical": "fatal", "trace": "debug"}.get(
        level, level
    )


def _find_root() -> Path:
    here = Path.cwd().resolve()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").exists() or (
            candidate / ".git"
        ).exists():
            return candidate
    return here


def _time() -> str:
    seconds, nanos = divmod(time.time_ns(), 1_000_000_000)
    return (
        time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(seconds))
        + f".{nanos:09d}Z"
    )


def _time_of(
    created: float,
) -> str:  # stdlib records carry a float: microsecond precision
    seconds, micros = divmod(round(created * 1_000_000), 1_000_000)
    return (
        time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(seconds))
        + f".{micros:06d}000Z"
    )


def _caller(path: str, line: int) -> str:
    shown = _caller_cache.get(path)
    if shown is None:
        resolved = Path(path).resolve()
        try:
            shown = f"{_root.name}/{resolved.relative_to(_root).as_posix()}"
        except ValueError:
            text = resolved.as_posix()
            shown = (
                text.split("site-packages/", 1)[1]
                if "site-packages/" in text
                else resolved.name
            )
        _caller_cache[path] = shown
    return f"{shown}:{line}"


def _trace_ids() -> dict[str, str]:
    if _otel_trace is None:
        return {}
    context = _otel_trace.get_current_span().get_span_context()
    if not context.is_valid:
        return {}
    return {
        "trace_id": format(context.trace_id, "032x"),
        "span_id": format(context.span_id, "016x"),
    }


def _safe(value: Any, depth: int = 0) -> Any:
    """JSON-native copy: long strings truncated, non-finite floats and unknown
    objects as text.
    """
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, str):
        return value if len(value) <= MAX_TEXT else value[:MAX_TEXT] + "..."
    if depth < 3 and isinstance(value, dict):
        return {str(k): _safe(v, depth + 1) for k, v in value.items()}
    if depth < 3 and isinstance(value, list | tuple | set):
        return [_safe(v, depth + 1) for v in value]
    return _safe(repr(value), depth)


def _write(
    level: str,
    name: str,
    message: str,
    fields: dict[str, Any],
    when: str,
    caller: str,
    exc: BaseException | None = None,
) -> None:
    event = getattr(
        jlogger.get_logger(name).with_values(**_identity), _JLOGGER[level]
    )()
    values: dict[str, Any] = {
        "time": when,
        "level": level,
        "logger": name,
        "caller": caller,
    }
    for key, value in fields.items():
        values[f"field_{key}" if key in RESERVED else key] = _safe(value)
    if exc is not None:
        values["error"] = _safe(str(exc))
        values["error_type"] = type(exc).__name__
        if level in ("error", "fatal"):
            values["stack"] = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )[-8000:]
    values.update(_trace_ids())
    event.with_values(**values).msg(_safe(message))


class Logger:
    """A named logger with optional bound fields.

    Methods: debug, info, warn, error, fatal, exception.
    """

    def __init__(self, name: str, bound: dict[str, Any]) -> None:
        self.name = name
        self._bound = bound

    def bind(self, **fields: Any) -> Logger:
        """A child that adds `fields` to every line (request_id, ...)."""
        return Logger(self.name, {**self._bound, **fields})

    def _log(
        self,
        level: str,
        message: str,
        fields: dict[str, Any],
        exc: BaseException | None = None,
    ) -> None:
        if _RANK[level] < _threshold:
            return  # disabled: no timestamp, no frame walk
        frame = sys._getframe(2)
        _write(
            level,
            self.name,
            message,
            {**self._bound, **fields},
            _time(),
            _caller(frame.f_code.co_filename, frame.f_lineno),
            exc,
        )
        if _error_hook is not None and level in ("error", "fatal"):
            try:
                _error_hook(self.name, message, exc)
            except Exception:  # noqa: BLE001
                pass  # reporting must never break the caller

    def debug(self, message: str, **fields: Any) -> None:
        self._log("debug", message, fields)

    def info(self, message: str, **fields: Any) -> None:
        self._log("info", message, fields)

    def warn(self, message: str, **fields: Any) -> None:
        self._log("warn", message, fields)

    def error(
        self, message: str, exc: BaseException | None = None, **fields: Any
    ) -> None:
        self._log("error", message, fields, exc)

    def fatal(
        self, message: str, exc: BaseException | None = None, **fields: Any
    ) -> None:
        self._log("fatal", message, fields, exc)

    def exception(
        self, message: str, exc: BaseException | None = None, **fields: Any
    ) -> None:
        """Error line for the exception being handled (or `exc`)."""
        self._log("error", message, fields, exc or sys.exc_info()[1])


class _StdlibBridge(logging.Handler):
    """Writes standard `logging` records (libraries, frameworks) in the
    unified format.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = _STDLIB.get(record.levelno) or (
                "fatal" if record.levelno > logging.CRITICAL else "debug"
            )
            if _RANK[level] < _threshold:
                return
            custom = getattr(record, "fields", None)
            exc = record.exc_info[1] if record.exc_info else None
            _write(
                level,
                record.name,
                record.getMessage(),
                dict(custom) if isinstance(custom, dict) else {},
                _time_of(record.created),
                _caller(record.pathname, record.lineno),
                exc,
            )
        except Exception:  # noqa: BLE001
            # A log line must never break the caller.
            self.handleError(record)
