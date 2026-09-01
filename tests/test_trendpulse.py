"""Regression tests for the canonical TrendPulse strategy boundary."""

import pandas as pd
import pytest

from strategies import trendpulse


def _series(rows: int = 100) -> pd.Series:
    index = pd.date_range(
        "2026-01-01 09:15", periods=rows, freq="1h", tz="Asia/Kolkata"
    )
    return pd.Series(range(100, 100 + rows), index=index, dtype=float)


def test_insufficient_data_returns_no_signal():
    close = _series(49)
    result = trendpulse(close, close, timestamp=close.index[-1])
    assert result.signal == "NO_SIGNAL"
    assert result.reason == "INSUFFICIENT_DATA"


def test_naive_timestamp_is_rejected():
    close = _series()
    with pytest.raises(ValueError, match="timezone-aware"):
        trendpulse(close, close, timestamp=pd.Timestamp("2026-01-01 10:15"))


def test_result_is_deterministic_for_same_input():
    close_1h = _series()
    close_4h = _series()
    first = trendpulse(close_1h, close_4h, timestamp=close_1h.index[-1])
    second = trendpulse(close_1h.copy(), close_4h.copy(), timestamp=close_1h.index[-1])
    assert first == second


def test_non_aligned_conditions_return_no_signal():
    close_1h = _series()
    close_4h = _series()
    result = trendpulse(close_1h, close_4h, timestamp=close_1h.index[-1])
    assert result.signal == "NO_SIGNAL"
