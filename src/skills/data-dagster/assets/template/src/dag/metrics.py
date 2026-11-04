"""dagster_* OTLP metrics, exported by a sensor.

Dagster has no metrics endpoint of its own. The daemon runs `metrics_sensor`
every 30 s; it reads the instance's event log after a cursor and records:

    dagster_runs_total{job,status}              success | failure | canceled
    dagster_run_duration_seconds{job}           histogram
    dagster_asset_materializations_total{asset}
    dagster_asset_check_failures_total{asset}
    dagster_asset_last_success_timestamp_seconds{asset}   gauge (freshness)
    dagster_metrics_sensor_last_tick_timestamp_seconds    gauge (heartbeat)

Labels are job and asset names only (bounded by the code, never by data).
Partition keys, run ids and error text are never labels.
"""

from __future__ import annotations

import socket
import threading
import time

from dagster import (
    DagsterEventType,
    DefaultSensorStatus,
    EventRecordsFilter,
    SensorEvaluationContext,
    SkipReason,
    sensor,
)
from opentelemetry.metrics import Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource

DURATION_BUCKETS_S = [1, 5, 15, 30, 60, 120, 300, 600, 1800, 3600, 7200]
RUN_EVENTS = {
    DagsterEventType.RUN_SUCCESS: "success",
    DagsterEventType.RUN_FAILURE: "failure",
    DagsterEventType.RUN_CANCELED: "canceled",
}


class DagsterMetrics:
    def __init__(self, provider: MeterProvider, service_name: str) -> None:
        self.provider = provider
        meter = provider.get_meter(service_name)
        self._runs = meter.create_counter("dagster_runs_total")
        self._duration = meter.create_histogram(
            "dagster_run_duration_seconds",
            explicit_bucket_boundaries_advisory=DURATION_BUCKETS_S,
        )
        self._materializations = meter.create_counter(
            "dagster_asset_materializations_total"
        )
        self._check_failures = meter.create_counter(
            "dagster_asset_check_failures_total"
        )
        self._lock = threading.Lock()
        self._last_success: dict[str, float] = {}
        self._last_tick = 0.0
        meter.create_observable_gauge(
            "dagster_asset_last_success_timestamp_seconds",
            callbacks=[self._observe_last_success],
        )
        meter.create_observable_gauge(
            "dagster_metrics_sensor_last_tick_timestamp_seconds",
            callbacks=[lambda _o: [Observation(self._last_tick)]],
        )

    def _observe_last_success(self, _options) -> list[Observation]:
        with self._lock:
            return [
                Observation(ts, {"asset": asset})
                for asset, ts in self._last_success.items()
            ]

    def run_finished(
        self, job: str, status: str, duration_s: float | None
    ) -> None:
        self._runs.add(1, {"job": job, "status": status})
        if duration_s is not None and status == "success":
            self._duration.record(max(0.0, duration_s), {"job": job})

    def materialized(self, asset: str) -> None:
        self._materializations.add(1, {"asset": asset})

    def check_failed(self, asset: str) -> None:
        self._check_failures.add(1, {"asset": asset})

    def set_last_success(self, asset: str, timestamp: float) -> None:
        with self._lock:
            self._last_success[asset] = timestamp

    def tick(self) -> None:
        self._last_tick = time.time()


def build_provider(endpoint: str, token: str, service: str, env: str):
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

    exporter = OTLPMetricExporter(
        endpoint=endpoint.rstrip("/") + "/v1/metrics",
        headers={"Authorization": f"Bearer {token}"} if token else None,
    )
    return MeterProvider(
        resource=Resource.create(
            {
                "service.name": service,
                "service.namespace": "platform",
                "deployment.environment": env,
                "host.name": socket.gethostname(),
            }
        ),
        metric_readers=[
            PeriodicExportingMetricReader(
                exporter, export_interval_millis=10_000
            )
        ],
    )


_metrics: DagsterMetrics | None = None


def set_metrics(metrics: DagsterMetrics | None) -> None:
    """Tests inject a DagsterMetrics built on an in-memory reader."""
    global _metrics
    _metrics = metrics


def get_metrics() -> DagsterMetrics | None:
    """Built once from the environment; None (a no-op) without an endpoint."""
    global _metrics
    from dag.settings import get_settings

    settings = get_settings()
    endpoint = settings.otel_endpoint
    if _metrics is None and endpoint:
        provider = build_provider(
            endpoint,
            settings.otel_auth_token.get_secret_value(),
            settings.service_name,
            settings.env_name,
        )
        _metrics = DagsterMetrics(provider, settings.service_name)
    return _metrics


def collect(context: SensorEvaluationContext, metrics: DagsterMetrics) -> int:
    """Record everything new since the cursor; return the new cursor."""
    instance = context.instance
    cursor = int(context.cursor or 0)
    newest = cursor
    for event_type, status in RUN_EVENTS.items():
        for record in instance.get_event_records(
            EventRecordsFilter(event_type=event_type, after_cursor=cursor)
        ):
            newest = max(newest, record.storage_id)
            event = record.event_log_entry.dagster_event
            duration = None
            run = instance.get_run_record_by_id(record.event_log_entry.run_id)
            if run and run.start_time and run.end_time:
                duration = run.end_time - run.start_time
            metrics.run_finished(event.job_name, status, duration)
    for record in instance.get_event_records(
        EventRecordsFilter(
            event_type=DagsterEventType.ASSET_MATERIALIZATION,
            after_cursor=cursor,
        )
    ):
        newest = max(newest, record.storage_id)
        metrics.materialized(record.asset_key.to_user_string())
    for record in instance.get_event_records(
        EventRecordsFilter(
            event_type=DagsterEventType.ASSET_CHECK_EVALUATION,
            after_cursor=cursor,
        )
    ):
        newest = max(newest, record.storage_id)
        evaluation = record.event_log_entry.dagster_event.event_specific_data
        if not evaluation.passed:
            metrics.check_failed(evaluation.asset_key.to_user_string())
    return newest


def refresh_freshness(context: SensorEvaluationContext, metrics) -> None:
    """The freshness gauge comes from the latest materialization of every
    asset, so it survives a daemon restart."""
    repository = context.repository_def
    keys = list(repository.assets_defs_by_key.keys())
    latest = context.instance.get_latest_materialization_events(keys)
    for key, event in latest.items():
        if event is not None:
            metrics.set_last_success(key.to_user_string(), event.timestamp)


@sensor(
    name="metrics_sensor",
    minimum_interval_seconds=30,
    default_status=DefaultSensorStatus.RUNNING,
)
def metrics_sensor(context: SensorEvaluationContext):
    metrics = get_metrics()
    if metrics is None:
        return SkipReason("OTEL_EXPORTER_OTLP_ENDPOINT is not set")
    metrics.tick()
    refresh_freshness(context, metrics)
    context.update_cursor(str(collect(context, metrics)))
    return SkipReason("metrics recorded")
