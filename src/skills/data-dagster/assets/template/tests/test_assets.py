import polars as pl
from dagster import materialize

from dag import assets
from dag.resources import OrdersSource


class FakeOrders(OrdersSource):
    def fetch(self, day):
        return [
            {"order_id": "o1", "symbol": " btc ", "price": 10.0, "qty": 1.0},
            {"order_id": "o1", "symbol": "btc", "price": 10.0, "qty": 1.0},
            {"order_id": "o2", "symbol": "eth", "price": 0.0, "qty": 1.0},
            {"order_id": "o3", "symbol": "eth", "price": 5.0, "qty": 2.0},
        ]


def run(source=None, key="2025-01-02"):
    return materialize(
        [assets.raw_orders, assets.clean_orders, assets.daily_summary],
        resources={"orders": source or FakeOrders()},
        partition_key=key,
        raise_on_error=False,
    )


def test_clean_orders_drops_invalid_and_duplicates():
    frame = pl.DataFrame(
        FakeOrders().fetch(None),
        schema_overrides=assets.RAW_SCHEMA,
    )
    clean = assets.clean_orders(frame)
    assert clean["order_id"].to_list() == ["o1", "o3"]
    assert clean["symbol"].to_list() == ["BTC", "ETH"]


def test_pipeline_materializes_every_asset():
    result = run()
    assert result.success
    keys = {
        e.asset_key.to_user_string()
        for e in result.get_asset_materialization_events()
    }
    assert keys == {"raw_orders", "clean_orders", "daily_summary"}


def test_empty_day_fails_the_blocking_check_path():
    class Empty(OrdersSource):
        def fetch(self, day):
            return []

    result = materialize(
        [assets.raw_orders, assets.clean_orders],
        resources={"orders": Empty()},
        partition_key="2025-01-03",
        raise_on_error=False,
    )
    checks = [c for c in result.get_asset_check_evaluations()]
    assert (
        any(c.check_name == "has_rows" and not c.passed for c in checks)
        or not result.success
    )
