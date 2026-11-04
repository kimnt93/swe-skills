from dagster import (
    DagsterInstance,
    build_sensor_context,
    materialize,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from dag import assets, definitions
from dag.metrics import DagsterMetrics, metrics_sensor, set_metrics
from tests.test_assets import FakeOrders


def points(reader, name):
    data = reader.get_metrics_data()
    found = []
    for resource in data.resource_metrics if data else []:
        for scope in resource.scope_metrics:
            for metric in scope.metrics:
                if metric.name == name:
                    found += list(metric.data.data_points)
    return found


def test_sensor_exports_runs_materializations_and_freshness():
    reader = InMemoryMetricReader()
    set_metrics(DagsterMetrics(MeterProvider(metric_readers=[reader]), "t"))
    instance = DagsterInstance.ephemeral()
    result = materialize(
        [assets.raw_orders, assets.clean_orders, assets.daily_summary],
        resources={"orders": FakeOrders()},
        partition_key="2025-01-02",
        instance=instance,
    )
    assert result.success
    context = build_sensor_context(
        instance=instance, repository_def=definitions.defs.get_repository_def()
    )
    metrics_sensor(context)
    materialised = points(reader, "dagster_asset_materializations_total")
    assert sum(p.value for p in materialised) == 3
    fresh = points(reader, "dagster_asset_last_success_timestamp_seconds")
    assert {p.attributes["asset"] for p in fresh} == {
        "raw_orders",
        "clean_orders",
        "daily_summary",
    }
    runs = points(reader, "dagster_runs_total")
    assert [(p.attributes["status"], p.value) for p in runs] == [
        ("success", 1)
    ]
    assert points(reader, "dagster_metrics_sensor_last_tick_timestamp_seconds")
    set_metrics(None)
