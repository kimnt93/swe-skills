"""Runs the table logic on a static table (no Kafka). Needs pathway and
pandas; skipped when they are not installed."""

import pytest

pw = pytest.importorskip("pathway")
pytest.importorskip("pandas")

from pipeline.pipeline import OrderIn, build  # noqa: E402


def rows():
    return [
        ("o1", " btc ", 100.01, 2.0, 0),
        ("o2", "btc", 100.02, 3.0, 10),
        ("o3", "eth", 0.0, 1.0, 20),  # invalid price: rejected
        ("o4", "btc", 100.03, 1.0, 70),  # next 60 s window
    ]


def table():
    return pw.debug.table_from_rows(OrderIn, rows())


def test_clean_drops_invalid_and_normalises():
    clean, rejected, _ = build(table(), 60)
    got = pw.debug.table_to_pandas(clean)
    bad = pw.debug.table_to_pandas(rejected)
    assert sorted(got["order_id"]) == ["o1", "o2", "o4"]
    assert set(got["symbol"]) == {"BTC"}
    assert list(bad["order_id"]) == ["o3"]


def test_window_aggregates_per_symbol():
    _, _, aggregate = build(table(), 60)
    df = pw.debug.table_to_pandas(aggregate).sort_values("window_start")
    assert list(df["orders"]) == [2, 1]
    assert list(df["qty"]) == [5.0, 1.0]
