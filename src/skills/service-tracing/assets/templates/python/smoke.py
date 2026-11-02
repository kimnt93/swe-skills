"""Smoke test and demo for service_tracing.py.

python3 smoke.py          assertions with in-memory exporters (no collector
                          needed)
python3 smoke.py demo     export one demo request to
                          OTEL_EXPORTER_OTLP_ENDPOINT (see
                          references/verification.md):
                          SERVICE_NAME=api TRACEPARENT=<from upstream> \\
                            DEMO_CALL=worker DEMO_DB=postgres \\
                            python3 smoke.py demo
                          prints the traceparent it sends downstream.
"""

import os
import sys

from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import SpanKind

from service_tracing import Options, Tracing


def make(service: str, **kw) -> tuple[Tracing, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    tracing = Tracing(
        Options(
            service=service,
            environment="test",
            node="n1",
            version="1.2.3",
            **kw,
        ),
        exporter,
        set_global=False,
        processor=SimpleSpanProcessor(exporter),
    )
    return tracing, exporter


def test() -> None:
    os.environ.update(
        POSTGRES_HOST="db.internal",
        POSTGRES_PORT="5432",
        KAFKA_BOOTSTRAP_SERVERS="k1:9092,k2:9092",
    )
    web, web_spans = make("web")
    api, api_spans = make("api")

    # identity + edge continuity: web CLIENT -> (headers) -> api SERVER, one
    # trace, parent = the client span
    with web.server_span("GET /home"):
        with web.client_span("GET /orders", peer="api") as headers:
            assert "traceparent" in headers
            with api.server_span("GET /orders", headers):
                with api.peer_span("postgres", "select orders"):
                    pass
    client = next(
        s for s in web_spans.get_finished_spans() if s.kind == SpanKind.CLIENT
    )
    server = next(
        s for s in api_spans.get_finished_spans() if s.kind == SpanKind.SERVER
    )
    assert server.context.trace_id == client.context.trace_id
    assert server.parent.span_id == client.context.span_id, (
        "server span must be a child of the caller's client span"
    )
    assert dict(server.resource.attributes)["service.name"] == "api"
    assert dict(client.resource.attributes)["deployment.environment"] == "test"
    assert dict(client.resource.attributes)["service.version"] == "1.2.3"

    # peer identity for an uninstrumented datastore
    db = next(
        s for s in api_spans.get_finished_spans() if s.kind == SpanKind.CLIENT
    )
    assert (
        db.attributes["peer.service"] == "postgres"
        and db.attributes["db.system"] == "postgresql"
    )
    assert (
        db.attributes["server.address"] == "db.internal"
        and db.attributes["server.port"] == 5432
    )
    assert db.name == "postgres select orders", (
        "span names are low-cardinality operations"
    )

    # messaging: producer -> headers -> consumer, same trace, consumer parent
    # = producer span
    with web.producer_span("orders.created") as msg_headers:
        pass
    with api.consumer_span(
        "orders.created", {k: v.encode() for k, v in msg_headers.items()}
    ):
        pass
    producer = next(
        s
        for s in web_spans.get_finished_spans()
        if s.kind == SpanKind.PRODUCER
    )
    consumer = next(
        s
        for s in api_spans.get_finished_spans()
        if s.kind == SpanKind.CONSUMER
    )
    assert (
        consumer.parent.span_id == producer.context.span_id
        and consumer.context.trace_id == producer.context.trace_id
    )

    # missing / invalid context starts a new valid trace and does not raise
    before = len(api_spans.get_finished_spans())
    for bad in (
        None,
        {},
        {"traceparent": "garbage"},
        {"traceparent": "00-" + "0" * 32 + "-" + "0" * 16 + "-01"},
    ):
        with api.server_span("GET /bad", bad) as span:
            assert span.get_span_context().is_valid
    roots = [
        s for s in api_spans.get_finished_spans()[before:] if s.parent is None
    ]
    assert len(roots) == 4

    # dependency mode records no internal spans; detailed mode
    # (TRACING_DETAIL) does
    with api.server_span("GET /x"):
        with api.detail_span("compute"):
            pass
    assert not any(
        s.kind == SpanKind.INTERNAL for s in api_spans.get_finished_spans()
    )
    detailed, detailed_spans = make("api", detail=True)
    with detailed.server_span("GET /x"):
        with detailed.detail_span("compute", items=3):
            pass
    assert (
        sum(
            s.kind == SpanKind.INTERNAL
            for s in detailed_spans.get_finished_spans()
        )
        == 1
    )

    # failures: error status, exception type only (no message in the status)
    try:
        with api.server_span("POST /fail"):
            raise ValueError("secret-token-123")
    except ValueError:
        pass
    failed = next(
        s for s in api_spans.get_finished_spans() if s.name == "POST /fail"
    )
    assert failed.status.status_code.name == "ERROR" and "secret" not in (
        failed.status.description or ""
    )

    # unsampled parent is honoured (parent-based): no span exported, ids
    # still valid for logs
    child_headers = {"traceparent": "00-" + "a" * 32 + "-" + "b" * 16 + "-00"}
    before = len(api_spans.get_finished_spans())
    with api.server_span("GET /unsampled", child_headers):
        pass
    assert len(api_spans.get_finished_spans()) == before

    # kafka peer: first bootstrap server
    with api.peer_span("kafka", "send") as _:
        pass
    k = api_spans.get_finished_spans()[-1]
    assert (
        k.kind == SpanKind.PRODUCER
        and k.attributes["server.address"] == "k1"
        and k.attributes["messaging.system"] == "kafka"
    )
    print("ok")


def demo() -> None:
    tracing = Tracing.from_env()
    inbound = (
        {"traceparent": os.environ["TRACEPARENT"]}
        if os.environ.get("TRACEPARENT")
        else None
    )
    with tracing.server_span("GET /demo", inbound):
        if os.environ.get("DEMO_DB"):
            with tracing.peer_span(os.environ["DEMO_DB"], "query"):
                pass
        if os.environ.get("DEMO_CALL"):
            with tracing.client_span(
                "GET /demo", peer=os.environ["DEMO_CALL"]
            ) as headers:
                print(headers["traceparent"])
    tracing.shutdown()


if __name__ == "__main__":
    demo() if sys.argv[1:] == ["demo"] else test()
