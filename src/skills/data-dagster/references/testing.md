# Testing a Dagster project

```python
result = materialize(
    [assets.raw_orders, assets.clean_orders, assets.daily_summary],
    resources={"orders": FakeOrders()},
    partition_key="2025-01-02",
)
assert result.success
```

- **Asset logic**: call the asset function directly with a polars frame (`assets.clean_orders(frame)`) for pure transforms.
- **Wiring**: `materialize([...], resources=..., partition_key=...)` runs the real graph in process with a fake resource. Assert
  success, the materialised keys, and (`result.get_asset_check_evaluations()`) the checks.
- **Failure paths**: an empty day, a duplicate id, a source error; assert the check fails or the run fails, not that nothing happens.
- **Sensor**: `build_sensor_context(instance=DagsterInstance.ephemeral(), repository_def=defs.get_repository_def())`, run a
  `materialize(..., instance=instance)`, call the sensor, and read an `InMemoryMetricReader`.
- **Definitions load**: `dagster definitions validate -m dag.definitions` in CI.
- No real database or Docker in unit tests; a live source check is one script run against a staging database.
