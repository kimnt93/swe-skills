#!/usr/bin/env python3
"""Micro-benchmarks behind the py-data recommendations. Run it on the target machine before arguing about libraries:

    pip install msgspec orjson ciso8601 polars pandas numpy python-dateutil
    python3 scripts/bench.py            # prints median ns/op (or ms) per library, fastest first

Each case reports the median of several repeats; numbers are relative evidence, not a promise.
"""

from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass
from datetime import datetime


def bench(fn, *, number: int, repeat: int = 7) -> float:
    """Median seconds per call."""
    runs = []
    for _ in range(repeat):
        start = time.perf_counter()
        for _ in range(number):
            fn()
        runs.append((time.perf_counter() - start) / number)
    return statistics.median(runs)


def table(title: str, rows: dict[str, float], unit: str, scale: float) -> None:
    print(f"\n{title}")
    best = min(rows.values())
    for name, seconds in sorted(rows.items(), key=lambda kv: kv[1]):
        print(f"  {name:<32} {seconds * scale:>10.2f} {unit}   x{seconds / best:.1f}")


def json_cases() -> None:
    import msgspec
    import orjson

    payload = {"id": "7c1e0c2e-6b7e-4a64-9a3b-0d6f5b1c9a11", "symbol": "TCH", "price": 12.35, "volume": 1200,
               "time": "2026-10-07T03:14:15.926Z", "bids": [[12.3, 100], [12.25, 200]], "asks": [[12.4, 50], [12.45, 75]]}
    raw = json.dumps(payload).encode()

    class Tick(msgspec.Struct):
        id: str
        symbol: str
        price: float
        volume: int
        time: str
        bids: list[tuple[float, int]]
        asks: list[tuple[float, int]]

    decode_struct = msgspec.json.Decoder(Tick).decode
    n = 20000
    table("JSON decode (one tick, 250 B)", {
        "json.loads": bench(lambda: json.loads(raw), number=n),
        "orjson.loads": bench(lambda: orjson.loads(raw), number=n),
        "msgspec decode -> dict": bench(lambda: msgspec.json.decode(raw), number=n),
        "msgspec decode -> Struct (typed)": bench(lambda: decode_struct(raw), number=n),
    }, "us/op", 1e6)
    tick = decode_struct(raw)
    table("JSON encode (one tick)", {
        "json.dumps": bench(lambda: json.dumps(payload), number=n),
        "orjson.dumps": bench(lambda: orjson.dumps(payload), number=n),
        "msgspec encode (Struct)": bench(lambda: msgspec.json.encode(tick), number=n),
    }, "us/op", 1e6)


def datetime_cases() -> None:
    import ciso8601
    from dateutil import parser as dateutil_parser

    text = "2026-10-07T03:14:15.926Z"
    n = 50000
    table("ISO 8601 / RFC 3339 timestamp parse", {
        "ciso8601.parse_datetime": bench(lambda: ciso8601.parse_datetime(text), number=n),
        "datetime.fromisoformat": bench(lambda: datetime.fromisoformat(text), number=n),
        "dateutil.parser.isoparse": bench(lambda: dateutil_parser.isoparse(text), number=n // 10),
        "datetime.strptime": bench(lambda: datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ"), number=n // 5),
    }, "us/op", 1e6)


def frame_cases() -> None:
    import numpy as np
    import pandas as pd
    import polars as pl

    rng = np.random.default_rng(0)
    rows = 2_000_000
    symbols = np.array([f"S{i:03d}" for i in range(500)])
    data = {"symbol": symbols[rng.integers(0, 500, rows)], "price": rng.random(rows) * 100, "volume": rng.integers(1, 1000, rows)}
    pdf = pd.DataFrame(data)
    pldf = pl.DataFrame(data)
    lazy = pldf.lazy()

    def pandas_job():
        pdf.assign(value=pdf.price * pdf.volume).groupby("symbol").agg(value=("value", "sum"), n=("value", "size"))

    def polars_job():
        pldf.group_by("symbol").agg((pl.col("price") * pl.col("volume")).sum().alias("value"), pl.len().alias("n"))

    def polars_lazy():
        lazy.group_by("symbol").agg((pl.col("price") * pl.col("volume")).sum().alias("value"), pl.len().alias("n")).collect()

    table(f"group-by aggregate over {rows:,} rows x 500 symbols", {
        "pandas": bench(pandas_job, number=1, repeat=5),
        "polars eager": bench(polars_job, number=1, repeat=5),
        "polars lazy (collect)": bench(polars_lazy, number=1, repeat=5),
    }, "ms/op", 1e3)

    def pandas_apply():
        pdf.head(200_000).apply(lambda r: r.price * r.volume, axis=1)

    def polars_expr():
        pldf.head(200_000).select(pl.col("price") * pl.col("volume"))

    table("row-wise Python callback vs expression (200k rows)", {
        "pandas apply(axis=1)": bench(pandas_apply, number=1, repeat=3),
        "polars expression": bench(polars_expr, number=1, repeat=5),
    }, "ms/op", 1e3)


if __name__ == "__main__":
    json_cases()
    datetime_cases()
    frame_cases()
