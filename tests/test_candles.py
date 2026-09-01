import pandas as pd
import pytest

from candles import (
    CandleValidationError,
    candle_close_timestamp,
    candle_display_range,
    candle_open_timestamp,
    closed_candles,
    is_hourly_observation,
)


def test_hourly_timestamp_represents_candle_close():
    timestamp = pd.Timestamp(
        "2026-08-31 10:15:00+05:30"
    )

    assert is_hourly_observation(timestamp)

    assert candle_open_timestamp(timestamp) == pd.Timestamp(
        "2026-08-31 09:15:00+05:30"
    )

    assert candle_close_timestamp(timestamp) == timestamp

    assert candle_display_range(timestamp) == "09:15-10:15"


def test_1115_candle_is_1016_to_1115():
    timestamp = pd.Timestamp(
        "2026-08-31 11:15:00+05:30"
    )

    assert candle_open_timestamp(timestamp) == pd.Timestamp(
        "2026-08-31 10:15:00+05:30"
    )

    assert candle_display_range(timestamp) == "10:16-11:15"


def test_1215_candle_is_1116_to_1215():
    timestamp = pd.Timestamp(
        "2026-08-31 12:15:00+05:30"
    )

    assert candle_display_range(timestamp) == "11:16-12:15"


def test_1315_candle_is_1216_to_1315():
    timestamp = pd.Timestamp(
        "2026-08-31 13:15:00+05:30"
    )

    assert candle_display_range(timestamp) == "12:16-13:15"


def test_1415_candle_is_1316_to_1415():
    timestamp = pd.Timestamp(
        "2026-08-31 14:15:00+05:30"
    )

    assert candle_display_range(timestamp) == "13:16-14:15"


def test_final_hourly_candle_is_1416_to_1515():
    timestamp = pd.Timestamp(
        "2026-08-31 15:15:00+05:30"
    )

    assert is_hourly_observation(timestamp)

    assert candle_display_range(timestamp) == "14:16-15:15"


def test_1516_is_not_a_canonical_hourly_close():
    timestamp = pd.Timestamp(
        "2026-08-31 15:16:00+05:30"
    )

    assert not is_hourly_observation(timestamp)

    with pytest.raises(CandleValidationError):
        candle_close_timestamp(timestamp)


def test_closed_candles_uses_candle_close_time():
    index = pd.DatetimeIndex(
        [
            "2026-08-31 10:15:00+05:30",
            "2026-08-31 11:15:00+05:30",
            "2026-08-31 15:15:00+05:30",
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


def test_1515_candle_is_not_closed_before_1515():
    index = pd.DatetimeIndex(
        [
            "2026-08-31 15:15:00+05:30",
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
            "2026-08-31 15:14:59+05:30"
        ),
    )

    assert result.empty
