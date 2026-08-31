"""Regression tests for the source-derived TrendPulse baseline."""

import pandas as pd
import pytest

from trendpulse import (
    EMA_FAST_1H,
    EMA_TREND_4H,
    RSI_PERIOD,
    ATR_PERIOD,
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL,
    MIN_1H_ROWS,
    MIN_4H_ROWS,
    MIN_ATR_PERCENT,
    evaluate_trendpulse,
)


def _frame(rows: int = 100) -> pd.DataFrame:
    index = pd.date_range(
        "2026-01-01 09:15", periods=rows, freq="1h", tz="Asia/Kolkata"
    )
    close = pd.Series(range(100, 100 + rows), index=index, dtype=float)
    return pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
        },
        index=index,
    )


def test_historical_parameters_are_locked_in_one_module():
    assert EMA_FAST_1H == 20
    assert EMA_TREND_4H == 50
    assert RSI_PERIOD == 14
    assert ATR_PERIOD == 14
    assert MACD_FAST == 12
    assert MACD_SLOW == 26
    assert MACD_SIGNAL == 9
    assert MIN_1H_ROWS == 50
    assert MIN_4H_ROWS == 15
    assert MIN_ATR_PERCENT == 0.2


def test_insufficient_1h_data_returns_no_signal():
    result = evaluate_trendpulse(_frame(49))
    assert result.trend == "NO_SIGNAL"
    assert result.reason == "INSUFFICIENT_1H_DATA"


def test_naive_timestamps_are_rejected():
    frame = _frame()
    frame.index = frame.index.tz_localize(None)
    with pytest.raises(ValueError, match="timezone-aware"):
        evaluate_trendpulse(frame)


def test_missing_ohlc_is_rejected():
    frame = _frame().drop(columns="close")
    with pytest.raises(ValueError, match="Missing required OHLC"):
        evaluate_trendpulse(frame)


def test_result_is_deterministic_for_same_input():
    frame = _frame()
    first = evaluate_trendpulse(frame)
    second = evaluate_trendpulse(frame.copy())
    assert first == second


def test_final_row_is_not_used_as_current_closed_candle():
    frame = _frame()
    base = evaluate_trendpulse(frame)
    changed = frame.copy()
    changed.iloc[-1, changed.columns.get_loc("close")] = 1_000_000
    changed.iloc[-1, changed.columns.get_loc("high")] = 1_000_001
    changed.iloc[-1, changed.columns.get_loc("open")] = 999_999
    result = evaluate_trendpulse(changed)
    assert result == base
