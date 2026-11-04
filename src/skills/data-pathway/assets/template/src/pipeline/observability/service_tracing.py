"""Service tracing for the dependency graph (see references/python.md and
references/env.md).

Copy this file into the service, build one `Tracing` at startup, and shut it
down on exit:

    # Reads SERVICE_NAME, RUN_ENV, OTEL_* ... (references/env.md).
    tracing = Tracing.from_env()
    try:
        run()
    finally:
        tracing.shutdown()

Default (dependency) mode records boundary spans only. Framework/driver
auto-instrumentation covers most hops; the helpers below cover the rest and
keep peer names stable:

    # Inbound hop (SERVER).
    with tracing.server_span("POST /orders", request.headers):
        # A datastore without instrumentation (CLIENT).
        with tracing.peer_span("postgres", "insert orders"):
            ...

        # Outbound call: the headers carry traceparent.
        with tracing.client_span("GET /pricing", peer="pricing") as headers:
            http.get(url, headers=headers)

        # Queue/stream publish (PRODUCER).
        with tracing.producer_span("orders.created") as headers:
            producer.send(topic, value, headers=list(headers.items()))

    # Message handler (CONSUMER).
    with tracing.consumer_span("orders.created", dict(message.headers)):
        ...

`detail_span()` is a no-op unless TRACING_DETAIL=true (detailed mode on
request). An empty endpoint (or OTEL_TRACES_EXPORTER=none /
OTEL_SDK_DISABLED=true) keeps every call a harmless no-op exporter: the
service must work without a collector.
"""

from __future__ import annotations

import contextlib
import os
import socket
from dataclasses import dataclass, field
from typing import Iterator, Mapping, MutableMapping
from urllib.parse import urlparse

from opentelemetry import context as otel_context
from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.propagators.composite import CompositeHTTPPropagator
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.sampling import (
    ALWAYS_OFF,
    ALWAYS_ON,
    ParentBased,
    TraceIdRatioBased,
)
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)
from opentelemetry.baggage.propagation import W3CBaggagePropagator

# kind -> (semantic attribute key, value, SpanKind, env prefix with host/port)
PEERS = {
    "postgres": ("db.system", "postgresql", SpanKind.CLIENT, "POSTGRES"),
    "redis": ("db.system", "redis", SpanKind.CLIENT, "REDIS"),
    "clickhouse": ("db.system", "clickhouse", SpanKind.CLIENT, "CLICKHOUSE"),
    "kafka": ("messaging.system", "kafka", SpanKind.PRODUCER, "KAFKA"),
    "s3": ("rpc.system", "aws-api", SpanKind.CLIENT, "S3"),
}


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _secret(name: str) -> str:
    """Value of NAME, else the contents of the file named by NAME_FILE."""
    value = _env(name)
    path = _env(name + "_FILE")
    if not value and path:
        with open(path, encoding="utf-8") as handle:
            value = handle.read().strip()
    return value


def _bool(name: str, default: bool = False) -> bool:
    raw = _env(name)
    return default if not raw else raw.lower() in ("1", "true", "yes", "on")


@dataclass
class Options:
    service: str
    environment: str = "local"
    node: str = ""
    version: str = ""
    endpoint: str = (
        ""  # OTLP/HTTP base URL; "/v1/traces" is appended. Empty = no export.
    )
    token: str = ""  # bearer token for the gateway
    timeout_s: float = 5.0
    sampler: str = "parentbased_traceidratio"
    sampler_arg: float = 1.0
    detail: bool = False
    resource_attributes: dict[str, str] = field(default_factory=dict)


class Tracing:
    def __init__(
        self,
        options: Options,
        exporter: SpanExporter | None = None,
        *,
        set_global: bool = True,
        processor: object | None = None,
    ) -> None:
        o = options
        node = o.node or socket.gethostname()
        attrs = {
            "service.name": o.service,
            "deployment.environment": o.environment,
            "deployment.environment.name": o.environment,
            "host.name": node,
            "service.instance.id": f"{node}-{os.getpid()}",
            **o.resource_attributes,
        }
        if o.version:
            attrs["service.version"] = o.version
        self.options = o
        self.provider = TracerProvider(
            resource=Resource.create(attrs), sampler=_sampler(o)
        )
        if (
            exporter is None
            and o.endpoint
            and _env("OTEL_TRACES_EXPORTER", "otlp") != "none"
            and not _bool("OTEL_SDK_DISABLED")
        ):
            exporter = OTLPSpanExporter(
                endpoint=o.endpoint.rstrip("/") + "/v1/traces",
                headers={"Authorization": f"Bearer {o.token}"}
                if o.token
                else None,
                timeout=o.timeout_s,
            )
        if exporter is not None:
            # Batch export off the request path; queue/batch sizes come from
            # the OTEL_BSP_* variables.
            self.provider.add_span_processor(
                processor or BatchSpanProcessor(exporter)
            )
        self.tracer = self.provider.get_tracer("service_tracing")
        propagate.set_global_textmap(
            CompositeHTTPPropagator(
                [TraceContextTextMapPropagator(), W3CBaggagePropagator()]
            )
        )
        if set_global:
            trace.set_tracer_provider(self.provider)

    @classmethod
    def from_env(
        cls, exporter: SpanExporter | None = None, **kwargs
    ) -> "Tracing":
        service = _env("OTEL_SERVICE_NAME") or _env("SERVICE_NAME")
        if not service:
            raise RuntimeError(
                "SERVICE_NAME (or OTEL_SERVICE_NAME) is required"
            )
        extra = dict(
            item.split("=", 1)
            for item in _env("OTEL_RESOURCE_ATTRIBUTES").split(",")
            if "=" in item
        )
        ratio = _env("OTEL_TRACES_SAMPLER_ARG", "1.0")
        options = Options(
            service=service,
            environment=_env("DEPLOYMENT_ENVIRONMENT")
            or _env("RUN_ENV")
            or _env("ENV_NAME")
            or "local",
            node=_env("NODE_NAME"),
            version=_env("SERVICE_VERSION")
            or extra.pop("service.version", ""),
            endpoint=_env("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT").removesuffix(
                "/v1/traces"
            )
            or _env("OTEL_EXPORTER_OTLP_ENDPOINT"),
            token=_secret("OTEL_AUTH_TOKEN"),
            timeout_s=float(_env("OTEL_EXPORTER_OTLP_TIMEOUT", "5000")) / 1000,
            sampler=_env("OTEL_TRACES_SAMPLER", "parentbased_traceidratio"),
            sampler_arg=float(ratio) if ratio else 1.0,
            detail=_bool("TRACING_DETAIL"),
            resource_attributes=extra,
        )
        return cls(options, exporter, **kwargs)

    def _start(self, name: str, **kwargs):
        # Failures are recorded by _guard/_fail (exception type only): the SDK
        # default would copy the message into the span status, and messages
        # can carry payload or credentials.
        return self.tracer.start_as_current_span(
            name,
            record_exception=False,
            set_status_on_exception=False,
            **kwargs,
        )

    # ---- boundary spans (dependency mode) ------------------------------
    @contextlib.contextmanager
    def server_span(
        self, name: str, headers: Mapping[str, str] | None = None, **attrs
    ) -> Iterator[trace.Span]:
        """Inbound request: continue the caller's trace from `headers`
        (missing or invalid -> a new trace).
        """
        ctx = propagate.extract(dict(headers or {}))
        with self._start(
            name, context=ctx, kind=SpanKind.SERVER, attributes=attrs
        ) as span:
            yield from self._guard(span)

    @contextlib.contextmanager
    def client_span(
        self, name: str, peer: str, **attrs
    ) -> Iterator[dict[str, str]]:
        """Outbound call to another service: yields the headers to send
        (traceparent...). `peer` is its service name.
        """
        with self._start(
            name,
            kind=SpanKind.CLIENT,
            attributes={"peer.service": peer, **attrs},
        ) as span:
            carrier: dict[str, str] = {}
            propagate.inject(carrier)
            try:
                yield carrier
            except BaseException as exc:
                _fail(span, exc)
                raise

    @contextlib.contextmanager
    def peer_span(
        self, kind: str, operation: str, **attrs
    ) -> Iterator[trace.Span]:
        """Datastore/broker/object store without its own instrumentation: a
        CLIENT span with a stable peer identity.

        Host/port come from the infrastructure variables (POSTGRES_HOST,
        KAFKA_BOOTSTRAP_SERVERS, S3_ENDPOINT ...).
        """
        key, value, span_kind, prefix = PEERS[kind]
        host, port = _peer_address(kind, prefix)
        peer = _env(f"PEER_SERVICE_{kind.upper()}") or kind
        attributes = {"peer.service": peer, key: value, **attrs}
        if host:
            attributes["server.address"] = host
        if port:
            attributes["server.port"] = port
        with self._start(
            f"{kind} {operation}", kind=span_kind, attributes=attributes
        ) as span:
            yield from self._guard(span)

    @contextlib.contextmanager
    def producer_span(
        self, destination: str, system: str = "kafka", **attrs
    ) -> Iterator[dict[str, str]]:
        """Publish to a queue/stream: yields the message headers that carry
        the context.
        """
        attributes = {
            "messaging.system": system,
            "messaging.destination.name": destination,
            "messaging.operation": "publish",
            "peer.service": _env(f"PEER_SERVICE_{system.upper()}") or system,
            **attrs,
        }
        with self._start(
            f"{destination} publish",
            kind=SpanKind.PRODUCER,
            attributes=attributes,
        ) as span:
            carrier: dict[str, str] = {}
            propagate.inject(carrier)
            try:
                yield carrier
            except BaseException as exc:
                _fail(span, exc)
                raise

    @contextlib.contextmanager
    def consumer_span(
        self,
        destination: str,
        headers: Mapping[str, str] | None = None,
        system: str = "kafka",
        **attrs,
    ) -> Iterator[trace.Span]:
        """Handle one message: parent = the producer's context from the
        message headers (bytes values are decoded).
        """
        carrier = {
            k: (v.decode() if isinstance(v, bytes) else v)
            for k, v in (headers or {}).items()
        }
        attributes = {
            "messaging.system": system,
            "messaging.destination.name": destination,
            "messaging.operation": "process",
            **attrs,
        }
        with self._start(
            f"{destination} process",
            context=propagate.extract(carrier),
            kind=SpanKind.CONSUMER,
            attributes=attributes,
        ) as span:
            yield from self._guard(span)

    # ---- detailed mode (only when TRACING_DETAIL=true) -----------------
    @contextlib.contextmanager
    def detail_span(self, name: str, **attrs) -> Iterator[trace.Span]:
        if not self.options.detail:
            yield trace.INVALID_SPAN
            return
        with self._start(
            name, kind=SpanKind.INTERNAL, attributes=attrs
        ) as span:
            yield from self._guard(span)

    # ---- helpers -------------------------------------------------------
    def inject(
        self, carrier: MutableMapping[str, str]
    ) -> MutableMapping[str, str]:
        propagate.inject(carrier)
        return carrier

    def traceparent(self) -> str:
        return self.inject({}).get("traceparent", "")

    @staticmethod
    def ids() -> tuple[str, str]:
        """(trace_id, span_id) of the active valid span as hex, else
        ('', '') - for log correlation.
        """
        ctx = trace.get_current_span().get_span_context()
        return (
            (f"{ctx.trace_id:032x}", f"{ctx.span_id:016x}")
            if ctx.is_valid
            else ("", "")
        )

    def shutdown(self) -> None:
        # Flushes the batch processor within its export timeout.
        self.provider.shutdown()

    @staticmethod
    def _guard(span: trace.Span) -> Iterator[trace.Span]:
        try:
            yield span
        except BaseException as exc:
            _fail(span, exc)
            raise


def _fail(span: trace.Span, exc: BaseException) -> None:
    span.set_status(
        Status(StatusCode.ERROR, type(exc).__name__)
    )  # type only: messages can leak data
    span.record_exception(exc, attributes={"exception.escaped": True})


def _sampler(o: Options):
    name = o.sampler.lower()
    if name in ("always_on", "parentbased_always_on"):
        return ALWAYS_ON if name == "always_on" else ParentBased(ALWAYS_ON)
    if name in ("always_off", "parentbased_always_off"):
        return ALWAYS_OFF if name == "always_off" else ParentBased(ALWAYS_OFF)
    if not 0.0 <= o.sampler_arg <= 1.0:
        raise ValueError(
            f"OTEL_TRACES_SAMPLER_ARG must be within 0..1, got {o.sampler_arg}"
        )
    ratio = TraceIdRatioBased(o.sampler_arg)
    return (
        ratio if name == "traceidratio" else ParentBased(ratio)
    )  # default: honour the upstream decision


def _peer_address(kind: str, prefix: str) -> tuple[str, int]:
    if kind == "kafka":
        first = _env("KAFKA_BOOTSTRAP_SERVERS").split(",")[0].strip()
        host, _, port = first.rpartition(":")
        return (host or first, int(port) if port.isdigit() and host else 0)
    if kind == "s3":
        url = urlparse(_env("S3_ENDPOINT"))
        return url.hostname or "", url.port or (
            443 if url.scheme == "https" else 80 if url.scheme else 0
        )
    default = {"postgres": 5432, "redis": 6379, "clickhouse": 9000}.get(
        kind, 0
    )
    port = _env(f"{prefix}_PORT")
    return _env(f"{prefix}_HOST"), int(port) if port.isdigit() else default
