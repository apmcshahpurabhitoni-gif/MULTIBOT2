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

# Timestamps represent CANDLE OPEN TIME.
# Therefore:
#   09:15 -> 09:15-10:15
#   10:15 -> 10:15-11:15
#   11:15 -> 11:15-12:15
#   12:15 -> 12:15-13:15
#   13:15 -> 13:15-14:15
#   14:15 -> 14:15-15:15
#
# The 15:15-15:30 remainder is not treated as a 1H candle.

HOURLY_OBSERVATION_TIMES: tuple[time, ...] = (
    time(9, 15),
    time(10, 15),
    time(11, 15),
    time(12, 15),
    time(13, 15),
    time(14, 15),
)

CANDLE_INTERVAL = pd.Timedelta(hours=1)


class CandleValidationError(ValueError):
    """Raised when candle timing or structure is invalid."""


def normalize_index(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    """Return a sorted DataFrame using canonical IST timestamps."""

    if not isinstance(
        frame.index,
        pd.DatetimeIndex,
    ):
        raise CandleValidationError(
            "Candle data must use a DatetimeIndex"
        )

    if frame.index.tz is None:
        raise CandleValidationError(
            "Candle timestamps must be timezone-aware"
        )

    result = frame.copy()

    result.index = result.index.tz_convert(
        IST_TIMEZONE
    )

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

    local = timestamp.tz_convert(
        IST_TIMEZONE
    )

    current = local.time()

    market_open = time.fromisoformat(
        NSE_MARKET_OPEN
    )

    market_close = time.fromisoformat(
        NSE_MARKET_CLOSE
    )

    return (
        market_open
        <= current
        <= market_close
    )


def is_hourly_observation(
    timestamp: pd.Timestamp,
) -> bool:
    """Return True for a canonical 1H candle open timestamp."""

    timestamp = pd.Timestamp(timestamp)

    if timestamp.tzinfo is None:
        raise CandleValidationError(
            "Timestamp must be timezone-aware"
        )

    local = timestamp.tz_convert(
        IST_TIMEZONE
    )

    return (
        local.time()
        in HOURLY_OBSERVATION_TIMES
    )


def candle_close_timestamp(
    timestamp: pd.Timestamp,
) -> pd.Timestamp:
    """Return the close time for a canonical 1H candle.

    Candle timestamps are open times, so a 14:15 candle is not
    closed until 15:15.
    """

    timestamp = pd.Timestamp(timestamp)

    if timestamp.tzinfo is None:
        raise CandleValidationError(
            "Timestamp must be timezone-aware"
        )

    if not is_hourly_observation(timestamp):
        raise CandleValidationError(
            "Timestamp is not a canonical 1H candle open time"
        )

    return timestamp.tz_convert(
        IST_TIMEZONE
    ) + CANDLE_INTERVAL


def closed_candles(
    frame: pd.DataFrame,
    *,
    as_of: pd.Timestamp,
) -> pd.DataFrame:
    """Return only 1H candles whose intervals have closed by ``as_of``."""

    result = normalize_index(frame)

    as_of = pd.Timestamp(as_of)

    if as_of.tzinfo is None:
        raise CandleValidationError(
            "as_of must be timezone-aware"
        )

    as_of = as_of.tz_convert(
        IST_TIMEZONE
    )

    closed_mask = result.index.map(
        lambda timestamp: candle_close_timestamp(timestamp)
        <= as_of
    )

    return result.loc[closed_mask]


def validate_hourly_observations(
    frame: pd.DataFrame,
) -> None:
    """Reject timestamps outside the canonical hourly open-time schedule."""

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
    """Keep only candles whose open timestamps are inside NSE session hours."""

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
    """Return the latest 1H candle whose full interval has closed."""

    closed = closed_candles(
        frame,
        as_of=as_of,
    )

    if closed.empty:
        return None

    return closed.iloc[-1]
