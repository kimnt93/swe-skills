"""Kafka -> Pathway -> Kafka.

Two outputs from one input: every valid order, cleaned (`topic_out`), and a
per-symbol tumbling-window aggregate (`topic_out` + ".agg"). Metrics follow
the shared stream_pipeline_* contract (data-pathway skill,
references/metric-contract.md).
"""

from __future__ import annotations

import time

import pathway as pw

from pipeline import transform
from pipeline.pipeline_metrics import PipelineMetrics
from pipeline.settings import Settings


class OrderIn(pw.Schema):
    order_id: str
    symbol: str
    price: float
    qty: float
    ts: int  # event time, epoch seconds


def build(orders: pw.Table, window_seconds: int):
    """The table logic, shared by production and the tests.

    Returns (clean, rejected, aggregate).
    """
    ok = pw.apply(
        transform.is_valid, pw.this.symbol, pw.this.price, pw.this.qty
    )
    rejected = orders.filter(~ok)
    clean = orders.filter(ok).select(
        order_id=pw.this.order_id,
        symbol=pw.apply(transform.normalise_symbol, pw.this.symbol),
        price_ticks=pw.apply(transform.price_to_ticks, pw.this.price),
        qty=pw.this.qty,
        ts=pw.this.ts,
    )
    aggregate = clean.windowby(
        pw.this.ts,
        window=pw.temporal.tumbling(duration=window_seconds),
        instance=pw.this.symbol,
    ).reduce(
        symbol=pw.this._pw_instance,
        window_start=pw.this._pw_window_start,
        orders=pw.reducers.count(),
        qty=pw.reducers.sum(pw.this.qty),
        last_price_ticks=pw.reducers.max(pw.this.price_ticks),
    )
    return clean, rejected, aggregate


def on_added(handler) -> None:
    """Call `handler(row)` for every row added to the table (not for
    retractions), without touching the table's own outputs."""

    def on_change(key, row, time, is_addition):
        if is_addition:
            handler(row)

    return on_change


def instrument(orders, clean, rejected, metrics: PipelineMetrics) -> None:
    """Count the three statuses from the table streams themselves."""

    def seen(row):
        metrics.received(event_ms=row["ts"] * 1000)

    def rejected_row(row):
        metrics.received()
        metrics.dropped()

    def published(row):
        late_ms = max(0.0, time.time() * 1000 - row["ts"] * 1000)
        metrics.published(latency_ms=late_ms)

    pw.io.subscribe(clean, on_change=on_added(published))
    pw.io.subscribe(rejected, on_change=on_added(rejected_row))
    # `received` for valid rows is counted when they are published, so each
    # arrival is counted exactly once: valid -> here, rejected -> above.
    pw.io.subscribe(clean, on_change=on_added(seen))


def persistence(settings: Settings):
    """Resume from disk after a restart (a mounted volume)."""
    if not settings.persistence_dir:
        return None
    backend = pw.persistence.Backend.filesystem(settings.persistence_dir)
    return pw.persistence.Config(backend)


def run(settings: Settings) -> None:
    metrics = PipelineMetrics(
        settings.service_name,
        environment=settings.env_name,
        endpoint=settings.otel_endpoint,
        token=settings.otel_auth_token.get_secret_value(),
    )
    metrics.set_kafka_healthy(True)
    orders = pw.io.kafka.read(
        settings.pathway_kafka(),
        topic=settings.kafka_topic_in,
        schema=OrderIn,
        format="json",
        autocommit_duration_ms=100,
    )
    clean, rejected, aggregate = build(orders, settings.window_seconds)
    instrument(orders, clean, rejected, metrics)
    pw.io.kafka.write(
        clean,
        settings.pathway_kafka(),
        topic_name=settings.kafka_topic_out,
        format="json",
    )
    pw.io.kafka.write(
        aggregate,
        settings.pathway_kafka(),
        topic_name=settings.kafka_topic_out + ".agg",
        format="json",
    )
    try:
        pw.run(persistence_config=persistence(settings))
    finally:
        metrics.shutdown()
