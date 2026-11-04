"""The code location: `dagster dev -m dag.definitions` or, in production,
the module named in pyproject.toml's [tool.dagster]."""

from __future__ import annotations

import os

from dagster import (
    AssetSelection,
    Definitions,
    build_schedule_from_partitioned_job,
    define_asset_job,
    load_asset_checks_from_modules,
    load_assets_from_modules,
)

from dag import assets
from dag.metrics import metrics_sensor
from dag.resources import PostgresOrders

all_assets = load_assets_from_modules([assets])
all_checks = load_asset_checks_from_modules([assets])

daily_job = define_asset_job(
    "daily_orders",
    selection=AssetSelection.groups("orders"),
    partitions_def=assets.DAILY,
)

# 01:15 UTC the next day: the source has settled; the run is of yesterday.
daily_schedule = build_schedule_from_partitioned_job(
    daily_job, hour_of_day=1, minute_of_hour=15
)

defs = Definitions(
    assets=all_assets,
    asset_checks=all_checks,
    jobs=[daily_job],
    schedules=[daily_schedule],
    sensors=[metrics_sensor],
    resources={
        "orders": PostgresOrders(
            host=os.environ.get("POSTGRES_HOST", "127.0.0.1"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            database=os.environ.get("POSTGRES_DB", "example"),
            user=os.environ.get("POSTGRES_USER", "example"),
        )
    },
)
