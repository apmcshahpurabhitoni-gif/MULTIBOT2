"""Canonical market-data boundary for MULTIBOT2.

This module deliberately does not select a provider yet. Provider selection is
still a Phase 0 decision under the ₹0 constraint. It defines the normalized
shape and validation boundary that every future provider must satisfy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


NSE_TIMEZONE = "Asia/Kolkata"


@dataclass(frozen=True)
class MarketSymbol:
    """Provider-independent symbol definition."""

    canonical: str
    display_name: str
    market: str = "NSE"


@dataclass(frozen=True)
class MarketData:
    """Normalized OHLCV market data."""

    symbol: MarketSymbol
    timeframe: str
    candles: pd.DataFrame
    source: str


def normalize_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize an OHLCV frame without choosing a data provider.

    Required columns are open/high/low/close. Volume is optional. The index
    must be timezone-aware and is converted to the canonical NSE timezone.
    """
    required = {"open", "high", "low", "close"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required OHLC columns: {sorted(missing)}")
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError("Market-data index must be a DatetimeIndex")
    if frame.index.tz is None:
        raise ValueError("Market-data index must be timezone-aware")

    result = frame.copy().sort_index()
    result.index = result.index.tz_convert(NSE_TIMEZONE)

    if result.index.has_duplicates:
        raise ValueError("Market-data index contains duplicate timestamps")
    if result.empty:
        return result

    numeric_columns = ["open", "high", "low", "close"]
    if "volume" in result.columns:
        numeric_columns.append("volume")
    result[numeric_columns] = result[numeric_columns].apply(pd.to_numeric, errors="coerce")
    if result[numeric_columns].isna().any().any():
        raise ValueError("Market-data OHLCV contains non-numeric or missing values")

    if (result["high"] < result[["open", "close"]].max(axis=1)).any():
        raise ValueError("Invalid OHLC data: high below open/close")
    if (result["low"] > result[["open", "close"]].min(axis=1)).any():
        raise ValueError("Invalid OHLC data: low above open/close")
    if (result["low"] > result["high"]).any():
        raise ValueError("Invalid OHLC data: low above high")

    return result


def validate_timeframe(timeframe: str) -> str:
    """Validate the canonical timeframe notation used by the application."""
    normalized = timeframe.strip().lower()
    allowed = {"1h", "4h"}
    if normalized not in allowed:
        raise ValueError(f"Unsupported timeframe: {timeframe!r}")
    return normalized


def validate_symbols(symbols: Iterable[MarketSymbol]) -> tuple[MarketSymbol, ...]:
    """Validate and freeze a symbol collection without inventing a universe."""
    values = tuple(symbols)
    if not values:
        raise ValueError("At least one market symbol is required")
    canonical = [symbol.canonical for symbol in values]
    if any(not value.strip() for value in canonical):
        raise ValueError("Canonical symbols cannot be empty")
    if len(set(canonical)) != len(canonical):
        raise ValueError("Duplicate canonical symbols are not allowed")
    return values
