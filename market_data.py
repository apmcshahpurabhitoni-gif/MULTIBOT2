"""Canonical market-data layer for MULTIBOT2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from config import IST_TIMEZONE


REQUIRED_OHLC = (
    "open",
    "high",
    "low",
    "close",
)


class MarketDataError(ValueError):
    """Raised when market data fails validation."""


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
            raise MarketDataError(
                "Candle timestamp must be timezone-aware"
            )

        prices = (
            self.open,
            self.high,
            self.low,
            self.close,
        )

        if any(pd.isna(value) for value in prices):
            raise MarketDataError(
                "Candle OHLC values cannot be NaN"
            )

        if any(float(value) <= 0 for value in prices):
            raise MarketDataError(
                "Candle OHLC values must be positive"
            )

        if self.high < max(
            self.open,
            self.close,
        ):
            raise MarketDataError(
                "Candle high is below open/close"
            )

        if self.low > min(
            self.open,
            self.close,
        ):
            raise MarketDataError(
                "Candle low is above open/close"
            )


def normalize_candles(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    """Normalize provider data into canonical IST OHLC data."""

    if not isinstance(
        frame,
        pd.DataFrame,
    ):
        raise TypeError(
            "Market data must be a pandas DataFrame"
        )

    missing = [
        column
        for column in REQUIRED_OHLC
        if column not in frame.columns
    ]

    if missing:
        raise MarketDataError(
            "Missing required OHLC columns: "
            + ", ".join(missing)
        )

    result = frame.copy()

    if not isinstance(
        result.index,
        pd.DatetimeIndex,
    ):
        raise MarketDataError(
            "Market-data index must be a DatetimeIndex"
        )

    if result.index.tz is None:
        raise MarketDataError(
            "Market-data timestamps must be timezone-aware"
        )

    result.index = result.index.tz_convert(
        IST_TIMEZONE
    )

    result = result.sort_index()

    if result.index.has_duplicates:
        raise MarketDataError(
            "Market-data timestamps must be unique"
        )

    for column in REQUIRED_OHLC:

        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        )

    if result[
        list(REQUIRED_OHLC)
    ].isna().any().any():

        raise MarketDataError(
            "OHLC data contains invalid values"
        )

    if (
        result[
            list(REQUIRED_OHLC)
        ] <= 0
    ).any().any():

        raise MarketDataError(
            "OHLC values must be positive"
        )

    invalid_high = (
        result["high"]
        < result[
            ["open", "close"]
        ].max(axis=1)
    )

    invalid_low = (
        result["low"]
        > result[
            ["open", "close"]
        ].min(axis=1)
    )

    if invalid_high.any():
        raise MarketDataError(
            "One or more candles have invalid highs"
        )

    if invalid_low.any():
        raise MarketDataError(
            "One or more candles have invalid lows"
        )

    return result


def candles_from_records(
    records: Iterable[dict],
) -> pd.DataFrame:
    """Convert provider-neutral candle records to canonical data."""

    records = list(records)

    if not records:

        return pd.DataFrame(
            columns=list(REQUIRED_OHLC),
            index=pd.DatetimeIndex(
                [],
                tz=IST_TIMEZONE,
            ),
        )

    frame = pd.DataFrame(records)

    if "timestamp" not in frame.columns:
        raise MarketDataError(
            "Every candle requires a timestamp"
        )

    timestamps = pd.to_datetime(
        frame.pop("timestamp"),
        errors="coerce",
    )

    if timestamps.isna().any():
        raise MarketDataError(
            "One or more candle timestamps are invalid"
        )

    if timestamps.dt.tz is None:
        raise MarketDataError(
            "Candle timestamps must be timezone-aware"
        )

    frame.index = timestamps.dt.tz_convert(
        IST_TIMEZONE
    )

    return normalize_candles(frame)


def validate_symbol(
    symbol: str,
) -> str:
    """Normalize and validate an NSE symbol."""

    if not isinstance(
        symbol,
        str,
    ):
        raise TypeError(
            "Symbol must be a string"
        )

    symbol = symbol.strip().upper()

    if not symbol:
        raise MarketDataError(
            "Symbol cannot be empty"
        )

    return symbol


def get_required_symbols() -> tuple[str, ...]:
    """Return the frozen MULTIBOT2 NSE-15 universe."""

    from config import NSE_15_SYMBOLS

    return NSE_15_SYMBOLS


def candle_age_hours(
    timestamp: pd.Timestamp,
    now: pd.Timestamp,
) -> float:
    """Return candle age in hours."""

    timestamp = pd.Timestamp(timestamp)
    now = pd.Timestamp(now)

    if timestamp.tzinfo is None:
        raise MarketDataError(
            "Candle timestamp must be timezone-aware"
        )

    if now.tzinfo is None:
        raise MarketDataError(
            "Current timestamp must be timezone-aware"
        )

    timestamp = timestamp.tz_convert(
        IST_TIMEZONE
    )

    now = now.tz_convert(
        IST_TIMEZONE
    )

    age = (
        now - timestamp
    ).total_seconds() / 3600

    if age < 0:
        raise MarketDataError(
            "Candle timestamp cannot be in the future"
        )

    return age
