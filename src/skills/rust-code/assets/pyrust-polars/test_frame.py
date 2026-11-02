import example_ta._native as native
import polars as pl


def test_frame_in_frame_out_with_null_warm_up():
    df = pl.DataFrame({"close": [1.0, 2.0, 3.0, 4.0]})
    out = native.ema_frame(df, "close", 3)
    assert out.columns == ["close", "close_ema"]
    assert out["close_ema"].to_list() == [None, None, 2.0, 3.0]
    assert out["close_ema"].null_count() == 2
