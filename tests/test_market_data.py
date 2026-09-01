import pandas as pd
import pytest

from market_data import (
    MarketDataError,
    candles_from_records,
    candle_age_hours,
    normalize_candles,
    validate_symbol,
)


def make_candles():
    index = pd.DatetimeIndex(
        [
            "2026-08-31 10:15:00+05:30",
            "2026-08-31 11:15:00+05:30",
        ]
    )

    return pd.DataFrame(
        {
            "open": [100.0, 101.0],
            "high": [103.0, 104.0],
            "low": [99.0, 100.0],
            "close": [102.0, 103.0],
        },
        index=index,
    )


def test_normalize_candles_accepts_valid_ohlc():
    result = normalize_candles(
        make_candles()
    )

    assert list(result.columns) == [
        "open",
        "high",
        "low",
        "close",
    ]

    assert len(result) == 2


def test_normalize_candles_sorts_timestamps():
    frame = make_candles().iloc[::-1]

    result = normalize_candles(frame)

    assert result.index.is_monotonic_increasing


def test_duplicate_timestamps_are_rejected():
    frame = make_candles()

    frame = pd.concat(
        [frame, frame.iloc[[0]]]
    )

    with pytest.raises(MarketDataError):
        normalize_candles(frame)


def test_naive_timestamps_are_rejected():
    frame = make_candles()

    frame.index = pd.DatetimeIndex(
        [
            "2026-08-31 10:15:00",
            "2026-08-31 11:15:00",
        ]
    )

    with pytest.raises(MarketDataError):
        normalize_candles(frame)


def test_missing_ohlc_column_is_rejected():
    frame = make_candles().drop(
        columns=["close"]
    )

    with pytest.raises(MarketDataError):
        normalize_candles(frame)


def test_nan_ohlc_is_rejected():
    frame = make_candles()

    frame.loc[
        frame.index[0],
        "close",
    ] = float("nan")

    with pytest.raises(MarketDataError):
        normalize_candles(frame)


def test_non_positive_prices_are_rejected():
    frame = make_candles()

    frame.loc[
        frame.index[0],
        "low",
    ] = 0

    with pytest.raises(MarketDataError):
        normalize_candles(frame)


def test_invalid_high_is_rejected():
    frame = make_candles()

    frame.loc[
        frame.index[0],
        "high",
    ] = 98

    with pytest.raises(MarketDataError):
        normalize_candles(frame)


def test_invalid_low_is_rejected():
    frame = make_candles()

    frame.loc[
        frame.index[0],
        "low",
    ] = 104

    with pytest.raises(MarketDataError):
        normalize_candles(frame)


def test_candles_from_records():
    records = [
        {
            "timestamp":
                "2026-08-31T10:15:00+05:30",
            "open": 100,
            "high": 103,
            "low": 99,
            "close": 102,
        },
        {
            "timestamp":
                "2026-08-31T11:15:00+05:30",
            "open": 102,
            "high": 105,
            "low": 101,
            "close": 104,
        },
    ]

    result = candles_from_records(records)

    assert len(result) == 2

    assert result.index.tz is not None


def test_empty_records_return_empty_ist_frame():
    result = candles_from_records([])

    assert result.empty

    assert result.index.tz is not None


def test_invalid_timestamp_is_rejected():
    records = [
        {
            "timestamp": "not-a-date",
            "open": 100,
            "high": 103,
            "low": 99,
            "close": 102,
        }
    ]

    with pytest.raises(MarketDataError):
        candles_from_records(records)


def test_validate_symbol_normalizes_symbol():
    assert (
        validate_symbol(" reliance ")
        == "RELIANCE"
    )


def test_empty_symbol_is_rejected():
    with pytest.raises(MarketDataError):
        validate_symbol("")


def test_candle_age_hours():
    timestamp = pd.Timestamp(
        "2026-08-31 10:15:00+05:30"
    )

    now = pd.Timestamp(
        "2026-08-31 11:15:00+05:30"
    )

    assert candle_age_hours(
        timestamp,
        now,
    ) == 1.0


def test_future_candle_is_rejected():
    timestamp = pd.Timestamp(
        "2026-08-31 12:15:00+05:30"
    )

    now = pd.Timestamp(
        "2026-08-31 11:15:00+05:30"
    )

    with pytest.raises(MarketDataError):
        candle_age_hours(
            timestamp,
            now,
        )
