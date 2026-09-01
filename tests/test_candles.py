import pandas as pd
import pytest

from candles import (
    CandleValidationError,
    candle_close_timestamp,
    closed_candles,
    is_hourly_observation,
)


def test_hourly_timestamp_represents_candle_open():
    timestamp = pd.Timestamp(
        "2026-08-31 09:15:00+05:30"
    )

    assert is_hourly_observation(timestamp)

    assert candle_close_timestamp(timestamp) == pd.Timestamp(
        "2026-08-31 10:15:00+05:30"
    )


def test_final_full_hourly_candle_closes_at_1515():
    timestamp = pd.Timestamp(
        "2026-08-31 14:15:00+05:30"
    )

    assert candle_close_timestamp(timestamp) == pd.Timestamp(
        "2026-08-31 15:15:00+05:30"
    )


def test_1515_is_not_a_canonical_hourly_open():
    timestamp = pd.Timestamp(
        "2026-08-31 15:15:00+05:30"
    )

    assert not is_hourly_observation(timestamp)

    with pytest.raises(CandleValidationError):
        candle_close_timestamp(timestamp)


def test_closed_candles_uses_candle_close_time():
    index = pd.DatetimeIndex(
        [
            "2026-08-31 09:15:00+05:30",
            "2026-08-31 10:15:00+05:30",
            "2026-08-31 14:15:00+05:30",
        ]
    )

    frame = pd.DataFrame(
        {
            "open": [100, 101, 105],
            "high": [102, 103, 107],
            "low": [99, 100, 104],
            "close": [101, 102, 106],
        },
        index=index,
    )

    result = closed_candles(
        frame,
        as_of=pd.Timestamp(
            "2026-08-31 15:15:00+05:30"
        ),
    )

    assert list(result.index) == list(index)


def test_1415_candle_is_not_closed_at_1415():
    index = pd.DatetimeIndex(
        [
            "2026-08-31 14:15:00+05:30",
        ]
    )

    frame = pd.DataFrame(
        {
            "open": [100],
            "high": [102],
            "low": [99],
            "close": [101],
        },
        index=index,
    )

    result = closed_candles(
        frame,
        as_of=pd.Timestamp(
            "2026-08-31 14:15:00+05:30"
        ),
    )

    assert result.empty
