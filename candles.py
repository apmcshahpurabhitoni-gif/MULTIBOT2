"""Canonical NSE candle/session rules for MULTIBOT2."""

from __future__ import annotations

from datetime import time

import pandas as pd

from config import IST_TIMEZONE

NSE_OPEN = time(9, 15)
NSE_CLOSE = time(15, 30)

# Confirmed hourly observation boundaries.
HOURLY_OBSERVATION_TIMES = (
    time(9, 15),
    time(10, 15),
    time(11, 15),
    time(12, 15),
    time(13, 15),
    time(14, 15),
)


class CandleValidationError(ValueError):
    """Raised when candle timing is invalid."""


def normalize_index(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a sorted DataFrame with a canonical IST DatetimeIndex."""

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


def is_nse_session_timestamp(timestamp: pd.Timestamp) -> bool:
    """Return whether a timestamp falls inside the NSE session."""

    timestamp = pd.Timestamp(timestamp)

    if timestamp.tzinfo is None:
        raise CandleValidationError(
            "Timestamp must be timezone-aware"
        )

    local = timestamp.tz_convert(IST_TIMEZONE)
    current = local.time()

    return NSE_OPEN <= current <= NSE_CLOSE


def is_hourly_observation(timestamp: pd.Timestamp) -> bool:
    """Return whether timestamp is a canonical 1H observation boundary."""

    timestamp = pd.Timestamp(timestamp)

    if timestamp.tzinfo is None:
        raise CandleValidationError(
            "Timestamp must be timezone-aware"
        )

    local = timestamp.tz_convert(IST_TIMEZONE)

    return local.time() in HOURLY_OBSERVATION_TIMES


def closed_candles(
    frame: pd.DataFrame,
    *,
    as_of: pd.Timestamp,
) -> pd.DataFrame:
    """Return candles whose timestamps are already closed as of ``as_of``.

    The currently forming candle is never passed to a strategy.
    """

    result = normalize_index(frame)

    as_of = pd.Timestamp(as_of)

    if as_of.tzinfo is None:
        raise CandleValidationError(
            "as_of must be timezone-aware"
        )

    as_of = as_of.tz_convert(IST_TIMEZONE)

    return result.loc[result.index <= as_of]


def validate_hourly_observations(frame: pd.DataFrame) -> None:
    """Validate that supplied candles use canonical hourly boundaries."""

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
            f"Unexpected hourly candle timestamp(s): {examples}"
        )
