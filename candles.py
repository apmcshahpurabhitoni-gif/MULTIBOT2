"""Canonical NSE candle and session rules for MULTIBOT2."""

from __future__ import annotations

from datetime import time

import pandas as pd

from config import (
    IST_TIMEZONE,
    NSE_MARKET_CLOSE,
    NSE_MARKET_OPEN,
)


# ============================================================
# CANONICAL 1H CANDLE CONVENTION
# ============================================================

# A 1H candle timestamp represents its CLOSE time.
# The minute range is therefore displayed as:
#
#   10:15 -> 09:15-10:15
#   11:15 -> 10:16-11:15
#   12:15 -> 11:16-12:15
#   13:15 -> 12:16-13:15
#   14:15 -> 13:16-14:15
#   15:15 -> 14:16-15:15
#
# The first 1H candle cannot be complete before 10:15.
# The 15:16-15:30 remainder is not treated as a 1H candle.

HOURLY_OBSERVATION_TIMES: tuple[time, ...] = (
    time(10, 15),
    time(11, 15),
    time(12, 15),
    time(13, 15),
    time(14, 15),
    time(15, 15),
)

CANDLE_INTERVAL = pd.Timedelta(hours=1)


class CandleValidationError(ValueError):
    """Raised when candle timing or structure is invalid."""


def normalize_index(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    """Return a sorted DataFrame using canonical IST timestamps."""

    if not isinstance(frame.index, pd.DatetimeIndex):
        raise CandleValidationError(
            "Candle data must use a DatetimeIndex"
        )

    if frame.index.tz is None:
        raise CandleValidationError(
            "Candle timestamps must be timezone-aware"
        )

    result = frame.copy()

    result.index = result.index.tz_convert(IST_TIMEZONE)
    result = result.sort_index()

    if result.index.has_duplicates:
        raise CandleValidationError(
            "Candle timestamps must be unique"
        )

    return result


def is_nse_session_timestamp(
    timestamp: pd.Timestamp,
) -> bool:
    """Return True when timestamp falls within NSE hours."""

    timestamp = pd.Timestamp(timestamp)

    if timestamp.tzinfo is None:
        raise CandleValidationError(
            "Timestamp must be timezone-aware"
        )

    local = timestamp.tz_convert(IST_TIMEZONE)
    current = local.time()

    market_open = time.fromisoformat(NSE_MARKET_OPEN)
    market_close = time.fromisoformat(NSE_MARKET_CLOSE)

    return market_open <= current <= market_close


def is_hourly_observation(
    timestamp: pd.Timestamp,
) -> bool:
    """Return True for a canonical 1H candle close timestamp."""

    timestamp = pd.Timestamp(timestamp)

    if timestamp.tzinfo is None:
        raise CandleValidationError(
            "Timestamp must be timezone-aware"
        )

    local = timestamp.tz_convert(IST_TIMEZONE)

    return local.time() in HOURLY_OBSERVATION_TIMES


def candle_close_timestamp(
    timestamp: pd.Timestamp,
) -> pd.Timestamp:
    """Return the canonical close time for a candle.

    The timestamp is already the candle close timestamp, so it is
    returned unchanged after validation.
    """

    timestamp = pd.Timestamp(timestamp)

    if timestamp.tzinfo is None:
        raise CandleValidationError(
            "Timestamp must be timezone-aware"
        )

    if not is_hourly_observation(timestamp):
        raise CandleValidationError(
            "Timestamp is not a canonical 1H candle close time"
        )

    return timestamp.tz_convert(IST_TIMEZONE)


def candle_open_timestamp(
    timestamp: pd.Timestamp,
) -> pd.Timestamp:
    """Return the beginning of the displayed 1H candle interval."""

    timestamp = pd.Timestamp(timestamp)

    if timestamp.tzinfo is None:
        raise CandleValidationError(
            "Timestamp must be timezone-aware"
        )

    if not is_hourly_observation(timestamp):
        raise CandleValidationError(
            "Timestamp is not a canonical 1H candle close time"
        )

    return timestamp.tz_convert(IST_TIMEZONE) - CANDLE_INTERVAL


def candle_display_range(
    timestamp: pd.Timestamp,
) -> str:
    """Return the human-readable minute range for a 1H candle.

    Examples:
        10:15 -> 09:15-10:15
        11:15 -> 10:16-11:15
    """

    close = pd.Timestamp(timestamp)

    if close.tzinfo is None:
        raise CandleValidationError(
            "Timestamp must be timezone-aware"
        )

    close = close.tz_convert(IST_TIMEZONE)

    if not is_hourly_observation(close):
        raise CandleValidationError(
            "Timestamp is not a canonical 1H candle close time"
        )

    open_time = candle_open_timestamp(close)

    display_start = open_time

    if close.time() != time(10, 15):
        display_start = open_time + pd.Timedelta(minutes=1)

    return (
        f"{display_start:%H:%M}-"
        f"{close:%H:%M}"
    )


def closed_candles(
    frame: pd.DataFrame,
    *,
    as_of: pd.Timestamp,
) -> pd.DataFrame:
    """Return only 1H candles whose close time has passed."""

    result = normalize_index(frame)

    as_of = pd.Timestamp(as_of)

    if as_of.tzinfo is None:
        raise CandleValidationError(
            "as_of must be timezone-aware"
        )

    as_of = as_of.tz_convert(IST_TIMEZONE)

    closed_mask = result.index.map(
        lambda timestamp: candle_close_timestamp(timestamp) <= as_of
    )

    return result.loc[closed_mask]


def validate_hourly_observations(
    frame: pd.DataFrame,
) -> None:
    """Reject timestamps outside the canonical hourly close-time schedule."""

    result = normalize_index(frame)

    invalid = [
        timestamp
        for timestamp in result.index
        if not is_hourly_observation(timestamp)
    ]

    if invalid:
        examples = ", ".join(
            timestamp.isoformat()
            for timestamp in invalid[:5]
        )

        raise CandleValidationError(
            "Unexpected hourly candle timestamp(s): "
            + examples
        )


def remove_out_of_session_candles(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    """Keep candles whose close timestamps are within NSE hours."""

    result = normalize_index(frame)

    mask = result.index.map(
        is_nse_session_timestamp
    )

    return result.loc[mask]


def latest_closed_candle(
    frame: pd.DataFrame,
    *,
    as_of: pd.Timestamp,
) -> pd.Series | None:
    """Return the latest 1H candle whose close time has passed."""

    closed = closed_candles(
        frame,
        as_of=as_of,
    )

    if closed.empty:
        return None

    return closed.iloc[-1]
