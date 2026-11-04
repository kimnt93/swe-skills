# Assets, partitions, checks, schedules

Template: `assets/template/src/dag/` (`assets.py`, `resources.py`, `definitions.py`).

## Assets

```python
@asset(partitions_def=DAILY, group_name="orders", kinds={"polars"})
def clean_orders(raw_orders: pl.DataFrame) -> pl.DataFrame: ...
```

- The function parameter name is the upstream asset: that is the dependency and the lineage edge.
- Return the data (the IO manager stores it) or a `MaterializeResult(metadata=...)` when the asset writes elsewhere itself.
  The template uses the default filesystem IO manager; for parquet use `dagster-polars`'s IO manager and point it at
  `OUTPUT_DIR`.
- Put row counts and similar facts in metadata (`MetadataValue.int`); they show in the UI and cost nothing.
- Do not use `from __future__ import annotations` in a module that defines assets: Dagster inspects the `context` annotation.

## Resources

`OrdersSource` is the abstract resource, `PostgresOrders` the real one, a fake in tests. Assets name the abstract type, so
swapping is one line in `Definitions(resources=...)`. SQL lives in a named multi-line constant (`ORDERS_SQL`) with bound
parameters; passwords come from `NAME_FILE`/`NAME` at connection time.

## Partitions and backfills

`DailyPartitionsDefinition(start_date=..., timezone="UTC")`. A run materialises one partition (`partition_key="2025-01-02"`);
a backfill selects a range in the UI or `dagster asset materialize --partition-range 2025-01-01...2025-01-31`. Downstream
partitions map one-to-one by default. Choose a partition unit that makes a re-run cheap and independent.

## Checks

```python
@asset_check(asset=clean_orders, blocking=True)
def no_duplicate_order_ids(clean_orders: pl.DataFrame) -> AssetCheckResult: ...
```

- `blocking=True` stops downstream assets when the check fails; use it for correctness (duplicates, nulls in keys), not for
  soft expectations.
- Checks that only warn (`has_rows`) still count in `dagster_asset_check_failures_total` so they show on the dashboard.

## Jobs and schedules

```python
daily_job = define_asset_job("daily_orders", selection=AssetSelection.groups("orders"), partitions_def=DAILY)
daily_schedule = build_schedule_from_partitioned_job(daily_job, hour_of_day=1, minute_of_hour=15)
```

The schedule launches the **previous** day's partition at 01:15 UTC. Pick the delay from when the source settles, not from
midnight. Use `@sensor` for event-driven runs (a file landed, an upstream asset updated) and keep `minimum_interval_seconds` ≥ 30.

## Retries and timeouts

Op-level `RetryPolicy(max_retries=3, delay=30, backoff=Backoff.EXPONENTIAL)` for transient I/O only. A deterministic failure
should fail fast. Set a run timeout with the `dagster/max_runtime` tag so a hung run is terminated and counted as a failure.
