"""Daily orders: raw -> clean -> summary. Partitioned by day, so a failed
day is re-run alone and a backfill is a partition range."""

from datetime import date

import polars as pl
from dagster import (
    AssetCheckResult,
    AssetExecutionContext,
    DailyPartitionsDefinition,
    MaterializeResult,
    MetadataValue,
    asset,
    asset_check,
)

from dag.resources import OrdersSource

DAILY = DailyPartitionsDefinition(start_date="2025-01-01", timezone="UTC")

RAW_SCHEMA = {
    "order_id": pl.String,
    "symbol": pl.String,
    "price": pl.Float64,
    "qty": pl.Float64,
}


@asset(partitions_def=DAILY, group_name="orders", kinds={"polars"})
def raw_orders(
    context: AssetExecutionContext, orders: OrdersSource
) -> pl.DataFrame:
    """The day's orders exactly as the source has them."""
    day = date.fromisoformat(context.partition_key)
    rows = orders.fetch(day)
    frame = pl.DataFrame(rows, schema_overrides=RAW_SCHEMA)
    context.add_output_metadata({"rows": MetadataValue.int(frame.height)})
    return frame


@asset(partitions_def=DAILY, group_name="orders", kinds={"polars"})
def clean_orders(raw_orders: pl.DataFrame) -> pl.DataFrame:
    """Valid rows only, symbols normalised, one row per order id."""
    return (
        raw_orders.filter(
            (pl.col("price") > 0)
            & (pl.col("qty") > 0)
            & (pl.col("symbol").str.strip_chars() != "")
        )
        .with_columns(pl.col("symbol").str.strip_chars().str.to_uppercase())
        .unique(subset="order_id", keep="first", maintain_order=True)
    )


@asset(partitions_def=DAILY, group_name="orders", kinds={"polars"})
def daily_summary(clean_orders: pl.DataFrame) -> MaterializeResult:
    """Orders and quantity per symbol."""
    summary = clean_orders.group_by("symbol").agg(
        pl.len().alias("orders"), pl.col("qty").sum().alias("qty")
    )
    return MaterializeResult(
        metadata={
            "symbols": MetadataValue.int(summary.height),
            "orders": MetadataValue.int(int(summary["orders"].sum() or 0)),
        }
    )


@asset_check(asset=clean_orders, blocking=True)
def no_duplicate_order_ids(clean_orders: pl.DataFrame) -> AssetCheckResult:
    duplicates = clean_orders.height - clean_orders["order_id"].n_unique()
    return AssetCheckResult(
        passed=duplicates == 0, metadata={"duplicates": duplicates}
    )


@asset_check(asset=clean_orders)
def has_rows(clean_orders: pl.DataFrame) -> AssetCheckResult:
    return AssetCheckResult(
        passed=clean_orders.height > 0, metadata={"rows": clean_orders.height}
    )
