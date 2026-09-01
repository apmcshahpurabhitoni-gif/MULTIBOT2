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
# CANONICAL 1H OBSERVATION TIMES
# ============================================================

HOURLY_OBSERVATION_TIMES: tuple[time, ...] = (
    time(9, 15),
    time(10, 15),
    time(11, 15),
    time(12, 15),
    time(13, 15),
    time(14, 15),
)


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
    """Return True for a canonical 1H observation boundary."""

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


def closed_candles(
    frame: pd.DataFrame,
    *,
    as_of: pd.Timestamp,
) -> pd.DataFrame:
    """Return candles that have closed by ``as_of``.

    A candle with a timestamp later than ``as_of`` is excluded.
    """

    result = normalize_index(frame)

    as_of = pd.Timestamp(as_of)

    if as_of.tzinfo is None:
        raise CandleValidationError(
            "as_of must be timezone-aware"
        )

    as_of = as_of.tz_convert(
        IST_TIMEZONE
    )

    return result.loc[
        result.index <= as_of
    ]


def validate_hourly_observations(
    frame: pd.DataFrame,
) -> None:
    """Reject timestamps outside the canonical hourly schedule."""

    result = normalize_index(frame)

    invalid = [
        timestamp
        for timestamp in result.index
        if not is_hourly_observation(
            timestamp
        )
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
    """Keep only candles occurring during NSE session hours."""

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
    """Return the latest candle known to be closed."""

    closed = closed_candles(
        frame,
        as_of=as_of,
    )

    if closed.empty:
        return None

    return closed.iloc[-1]
