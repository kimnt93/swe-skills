"""Rust-powered indicators. A thin layer over `example_ta._native`.

No arithmetic lives here: every symbol is a re-export of the native one.
"""

from ._native import (
    ExampleTaError,
    ExponentialMovingAverage,
    InvalidPeriodError,
    ema,
)

__all__ = [
    "ExampleTaError",
    "ExponentialMovingAverage",
    "InvalidPeriodError",
    "ema",
]
