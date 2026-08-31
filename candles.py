"""Canonical candle-time rules for MULTIBOT2.

The candle layer owns timestamp validation and the locked NIFTY/BANK NIFTY
1H observation schedule. It never evaluates a trading strategy.
"""

from __future__ import annotations

from datetime import time

import pandas as pd

NSE_TIMEZONE = "Asia/Kolkata"
SWEEP_1H_TIMES = (
    time(9, 15),
    time(10, 15),
    time(11, 15),
    time(12, 15),
    time(13, 15),
    time(14, 15),
)


def ensure_nse_index(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a sorted copy with a unique, timezone-aware NSE index."""
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError("Candle index must be a DatetimeIndex")
    if frame.index.tz is None:
        raise ValueError("Candle index must be timezone-aware")

    result = frame.copy().sort_index()
    result.index = result.index.tz_convert(NSE_TIMEZONE)
    if result.index.has_duplicates:
        raise ValueError("Candle index contains duplicate timestamps")
    return result


def is_sweep_observation_time(timestamp: pd.Timestamp) -> bool:
    """Whether a timestamp is one of the locked 1H Sweep observations."""
    if timestamp.tzinfo is None:
        raise ValueError("Timestamp must be timezone-aware")
    local = timestamp.tz_convert(NSE_TIMEZONE)
    return local.time() in SWEEP_1H_TIMES


def closed_candles(
    frame: pd.DataFrame, *, as_of: pd.Timestamp
) -> pd.DataFrame:
    """Return only candles whose close timestamp is at or before ``as_of``.

    This prevents the currently forming candle from entering confirmed signal
    calculations. Both timestamps must be timezone-aware.
    """
    normalized = ensure_nse_index(frame)
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    cutoff = as_of.tz_convert(NSE_TIMEZONE)
    return normalized.loc[normalized.index <= cutoff]


def validate_sweep_schedule(frame: pd.DataFrame) -> None:
    """Reject unexpected 1H observation timestamps for the Sweep layer."""
    normalized = ensure_nse_index(frame)
    invalid = [ts for ts in normalized.index if not is_sweep_observation_time(ts)]
    if invalid:
        raise ValueError(
            "Unexpected Sweep candle timestamp(s): "
            + ", ".join(ts.isoformat() for ts in invalid[:5])
        )
