"""Pipeline metrics: the shared stream_pipeline_* OTLP set (see
references/metric-contract.md).

Copy this file into the service, build one PipelineMetrics at startup, and
call the recording methods from the hot path. Requires opentelemetry-sdk and
opentelemetry-exporter-otlp-proto-http.

    metrics = PipelineMetrics(
        os.environ["SERVICE_NAME"],
        environment="stg",
        endpoint=OTLP_URL,
    )

    # Every message that arrives.
    metrics.received()
    # ... that is deliberately not forwarded.
    metrics.dropped()
    # After the ack / write.
    metrics.published(bytes=len(payload), latency_ms=elapsed_ms)
    # Flushes the last export.
    metrics.shutdown()
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Callable

from opentelemetry import metrics as otel_metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

LATENCY_BUCKETS_MS = [
    1,
    2,
    5,
    10,
    25,
    50,
    100,
    250,
    500,
    1000,
    2500,
    5000,
    10000,
    30000,
    60000,
]


class PipelineMetrics:
    def __init__(
        self,
        service_name: str,
        *,
        environment: str,
        endpoint: str = "",
        token: str = "",
        node_name: str | None = None,
        export_interval_ms: int = 10_000,
        ingestion: bool = False,
    ) -> None:
        """`service_name` is the pipeline name, e.g. feed-ws-transform. An
        empty `endpoint` keeps every call a no-op. `ingestion=True` adds the
        feed metrics. Construction counts a restart and marks the pipeline
        running.
        """
        self.provider: MeterProvider | None = None
        if endpoint:
            exporter = OTLPMetricExporter(
                endpoint=endpoint.rstrip("/") + "/v1/metrics",
                headers={"Authorization": f"Bearer {token}"}
                if token
                else None,
            )
            self.provider = MeterProvider(
                resource=Resource.create(
                    {
                        "service.name": service_name,
                        "service.namespace": "platform",
                        "deployment.environment": environment,
                        "host.name": node_name or socket.gethostname(),
                    }
                ),
                metric_readers=[
                    PeriodicExportingMetricReader(
                        exporter, export_interval_millis=export_interval_ms
                    )
                ],
            )
        # Use the provider's own meter: the global one can only be set once
        # per process.
        meter = (self.provider or otel_metrics).get_meter(service_name)
        self._messages = meter.create_counter("stream_pipeline_messages_total")
        self._bytes = meter.create_counter(
            "stream_pipeline_payload_bytes_total"
        )
        # No unit on the histogram: a unit makes Mimir rename it
        # ..._ms_milliseconds_bucket.
        self._latency = meter.create_histogram(
            "stream_pipeline_latency_ms",
            explicit_bucket_boundaries_advisory=LATENCY_BUCKETS_MS,
        )
        self._errors = meter.create_counter("stream_pipeline_errors_total")
        self._restarts = meter.create_counter("stream_pipeline_restarts_total")
        self._lock = threading.Lock()
        self._running = 0
        self._connected = 0
        self._kafka_ok = 0
        self._last_input_ms = 0
        self._started_at = time.time()
        self._backlog: Callable[[], int] | None = None
        self._in_flight: Callable[[], int] | None = None
        self._ingestion = ingestion
        gauge = meter.create_observable_gauge
        gauge(
            "stream_pipeline_running",
            callbacks=[lambda _o: [Observation(self._running)]],
        )
        gauge(
            "stream_pipeline_kafka_healthy",
            callbacks=[lambda _o: [Observation(self._kafka_ok)]],
        )
        gauge(
            "stream_pipeline_start_timestamp_seconds",
            callbacks=[lambda _o: [Observation(self._started_at)]],
        )
        gauge("stream_pipeline_last_message_age_ms", callbacks=[self._age])
        gauge(
            "stream_pipeline_latest_event_timestamp_seconds",
            callbacks=[self._latest],
        )
        gauge(
            "stream_pipeline_consumer_lag",
            callbacks=[lambda _o: self._call(self._backlog)],
        )
        if ingestion:
            self._reconnects = meter.create_counter(
                "stream_pipeline_reconnects_total"
            )
            gauge(
                "stream_pipeline_connection_active",
                callbacks=[lambda _o: [Observation(self._connected)]],
            )
            gauge(
                "stream_pipeline_in_flight",
                callbacks=[lambda _o: self._call(self._in_flight)],
            )
        self._restarts.add(1)
        self._running = 1

    # -- gauge callbacks ---------------------------------------------------- #

    def _age(self, _options: CallbackOptions) -> list[Observation]:
        with self._lock:
            last = self._last_input_ms
        return (
            [Observation(max(0, int(time.time() * 1000) - last))]
            if last
            else []
        )

    def _latest(self, _options: CallbackOptions) -> list[Observation]:
        with self._lock:
            last = self._last_input_ms
        return [Observation(last / 1000)] if last else []

    @staticmethod
    def _call(source: Callable[[], int] | None) -> list[Observation]:
        return [Observation(source())] if source else []

    # -- lifecycle ---------------------------------------------------------- #

    def shutdown(self) -> None:
        self._running = 0
        self._connected = 0
        if self.provider:
            self.provider.force_flush()
            self.provider.shutdown()

    def set_backlog(self, source: Callable[[], int]) -> None:
        """Messages waiting: Kafka lag for consumers, queue depth for
        ingestion.
        """
        self._backlog = source

    def set_in_flight(self, source: Callable[[], int]) -> None:
        """Ingestion: messages handed to the Kafka client and not yet
        acknowledged.
        """
        self._in_flight = source

    def set_kafka_healthy(self, healthy: bool) -> None:
        self._kafka_ok = int(healthy)

    def set_connected(self, connected: bool) -> None:
        """Ingestion: whether the feed connection is up."""
        self._connected = int(connected)

    def reconnect(self) -> None:
        if self._ingestion:
            self._reconnects.add(1)

    # -- recording ---------------------------------------------------------- #

    def received(
        self, count: int = 1, *, live: bool = True, event_ms: int | None = None
    ) -> None:
        """Every arrival. `live=False` (heartbeats, replays) counts but does
        not refresh the freshness gauges. `event_ms` is the Kafka timestamp or
        event time, default now.
        """
        self._messages.add(count, {"status": "received"})
        if live:
            with self._lock:
                self._last_input_ms = max(
                    self._last_input_ms, event_ms or int(time.time() * 1000)
                )

    def dropped(self, count: int = 1) -> None:
        """Arrived but deliberately not forwarded; also call received()."""
        self._messages.add(count, {"status": "dropped"})

    def published(
        self,
        count: int = 1,
        *,
        bytes: int = 0,
        latency_ms: float | None = None,
    ) -> None:
        """Forwarded: Kafka ack, sink write, or handled successfully."""
        self._messages.add(count, {"status": "published"})
        if bytes:
            self._bytes.add(bytes)
        if latency_ms is not None:
            self._latency.record(max(0.0, latency_ms))

    def error(self, count: int = 1) -> None:
        self._errors.add(count)
