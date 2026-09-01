"""Market-data contracts for MULTIBOT2.

This module defines the canonical data shape used by strategies, backtests,
and the dashboard. Provider-specific code must normalize into this shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

import pandas as pd

from config import IST_TIMEZONE


REQUIRED_OHLC_COLUMNS = ("open", "high", "low", "close")


class MarketDataError(ValueError):
    """Raised when market data fails canonical validation."""


@dataclass(frozen=True)
class Candle:
    """One normalized OHLC candle."""

    timestamp: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None

    def __post_init__(self) -> None:
        timestamp = pd.Timestamp(self.timestamp)

        if timestamp.tzinfo is None:
            raise MarketDataError("Candle timestamp must be timezone-aware")

        if not timestamp.tz_convert(IST_TIMEZONE):
            raise MarketDataError("Invalid candle timestamp")

        prices = (self.open, self.high, self.low, self.close)

        if any(pd.isna(value) for value in prices):
            raise MarketDataError("Candle OHLC values cannot be NaN")

        if any(float(value) <= 0 for value in prices):
            raise MarketDataError("Candle OHLC values must be positive")

        if self.high < max(self.open, self.close):
            raise MarketDataError("Candle high is below open/close")

        if self.low > min(self.open, self.close):
            raise MarketDataError("Candle low is above open/close")


def normalize_candles(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize a provider DataFrame into the canonical candle format."""

    if not isinstance(frame, pd.DataFrame):
        raise TypeError("Market data must be a pandas DataFrame")

    missing = [
        column
        for column in REQUIRED_OHLC_COLUMNS
        if column not in frame.columns
    ]

    if missing:
        raise MarketDataError(
            f"Missing required OHLC columns: {', '.join(missing)}"
        )

    result = frame.copy()

    if not isinstance(result.index, pd.DatetimeIndex):
        raise MarketDataError("Market-data index must be a DatetimeIndex")

    if result.index.tz is None:
        raise MarketDataError(
            "Market-data timestamps must be timezone-aware"
        )

    result.index = result.index.tz_convert(IST_TIMEZONE)
    result = result.sort_index()

    if result.index.has_duplicates:
        raise MarketDataError(
            "Market-data timestamps must be unique"
        )

    for column in REQUIRED_OHLC_COLUMNS:
        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        )

    if result[list(REQUIRED_OHLC_COLUMNS)].isna().any().any():
        raise MarketDataError("OHLC data contains invalid values")

    if (result[list(REQUIRED_OHLC_COLUMNS)] <= 0).any().any():
        raise MarketDataError("OHLC values must be positive")

    invalid_high = (
        result["high"]
        < result[["open", "close"]].max(axis=1)
    )

    invalid_low = (
        result["low"]
        > result[["open", "close"]].min(axis=1)
    )

    if invalid_high.any() or invalid_low.any():
        raise MarketDataError("Invalid OHLC candle geometry")

    return result


def candles_from_records(
    records: Iterable[dict],
) -> pd.DataFrame:
    """Build and normalize candles from provider-neutral records."""

    rows = list(records)

    if not rows:
        return pd.DataFrame(
            columns=list(REQUIRED_OHLC_COLUMNS),
            index=pd.DatetimeIndex([], tz=IST_TIMEZONE),
        )

    frame = pd.DataFrame(rows)

    if "timestamp" not in frame.columns:
        raise MarketDataError(
            "Market-data records require a timestamp"
        )

    timestamps = pd.to_datetime(
        frame.pop("timestamp"),
        errors="coerce",
    )

    if timestamps.isna().any():
        raise MarketDataError("Invalid candle timestamp")

    if timestamps.dt.tz is None:
        raise MarketDataError(
            "Market-data timestamps must be timezone-aware"
        )

    frame.index = timestamps.dt.tz_convert(IST_TIMEZONE)

    return normalize_candles(frame)


def candle_at(
    frame: pd.DataFrame,
    timestamp: datetime | pd.Timestamp,
) -> pd.Series:
    """Return one canonical candle by timestamp."""

    normalized = normalize_candles(frame)

    target = pd.Timestamp(timestamp)

    if target.tzinfo is None:
        raise MarketDataError(
            "Requested timestamp must be timezone-aware"
        )

    target = target.tz_convert(IST_TIMEZONE)

    try:
        return normalized.loc[target]
    except KeyError as exc:
        raise MarketDataError(
            f"No candle exists at {target.isoformat()}"
        ) from exc
