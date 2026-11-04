"""Pure business logic. No pathway import: it is tested with plain pytest
and called from the pipeline through pw.apply / pw.udf."""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal

TICK = Decimal("0.01")


def normalise_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def price_to_ticks(price: float) -> int:
    """Exact: go through Decimal(str(...)), never float arithmetic."""
    ticks = (Decimal(str(price)) / TICK).to_integral_value(ROUND_HALF_EVEN)
    return int(ticks)


def is_valid(symbol: str, price: float, qty: float) -> bool:
    """False rows are dropped (counted as `dropped`), not errors."""
    return bool(symbol.strip()) and price > 0 and qty > 0
