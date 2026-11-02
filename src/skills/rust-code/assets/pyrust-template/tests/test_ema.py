from __future__ import annotations

import threading
import time

import example_ta as ta
import numpy as np
import pytest


def test_warm_up_then_smoothing():
    e = ta.ExponentialMovingAverage(3)
    assert [e.update(x) for x in (1.0, 2.0)] == [None, None]
    assert e.update(3.0) == 2.0
    assert e.update(4.0) == pytest.approx(3.0)
    assert e.value == pytest.approx(3.0)


def test_bulk_equals_scalar_replay():
    xs = np.arange(1.0, 50.0)
    bulk = ta.ema(xs, 5)
    e = ta.ExponentialMovingAverage(5)
    scalar = np.array(
        [np.nan if (v := e.update(x)) is None else v for x in xs]
    )
    np.testing.assert_allclose(bulk, scalar, equal_nan=True)


def test_extend_keeps_state_like_scalar_replay():
    e1, e2 = ta.ExponentialMovingAverage(4), ta.ExponentialMovingAverage(4)
    xs = np.linspace(1, 10, 20)
    e1.extend(xs)
    for x in xs:
        e2.update(float(x))
    assert e1.value == pytest.approx(e2.value)


def test_errors_map_to_python_exceptions():
    with pytest.raises(ta.InvalidPeriodError):
        ta.ExponentialMovingAverage(0)
    with pytest.raises(ta.ExampleTaError):  # the base class catches it too
        ta.ema(np.ones(3), 0)
    with pytest.raises(ValueError, match="contiguous"):
        ta.ema(np.ones(10)[::2], 2)


def test_negative_period_is_rejected_by_the_type():
    with pytest.raises(OverflowError):
        ta.ExponentialMovingAverage(-1)


def test_nan_input_is_ignored_not_zeroed():
    e = ta.ExponentialMovingAverage(2)
    e.update(1.0)
    e.update(float("nan"))
    assert e.update(3.0) == 2.0


def test_the_gil_is_released_during_bulk_work():
    """A second thread keeps running while a long native call executes."""
    xs = np.random.default_rng(0).random(30_000_000)
    ticks = 0
    done = threading.Event()

    def ticker():
        nonlocal ticks
        while not done.is_set():
            ticks += 1
            time.sleep(0.001)

    t = threading.Thread(target=ticker)
    t.start()
    start = time.perf_counter()
    ta.ema(xs, 10)
    elapsed = time.perf_counter() - start
    done.set()
    t.join()
    # with the GIL held the ticker could not run at all during the call
    assert ticks >= 2 or elapsed < 0.01
