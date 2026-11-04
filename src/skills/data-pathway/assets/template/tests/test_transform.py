from pipeline import transform


def test_symbol_is_trimmed_and_upper():
    assert transform.normalise_symbol("  btc-usd ") == "BTC-USD"


def test_price_to_ticks_is_exact():
    assert transform.price_to_ticks(0.1 + 0.2) == 30
    assert transform.price_to_ticks(19.99) == 1999


def test_invalid_rows_are_rejected():
    assert transform.is_valid("BTC", 10.0, 1.0)
    assert not transform.is_valid(" ", 10.0, 1.0)
    assert not transform.is_valid("BTC", 0.0, 1.0)
    assert not transform.is_valid("BTC", 10.0, -1.0)
