"""Canonical strategy boundary for MULTIBOT2.

Both strategies return normalized signal classifications. Execution, Telegram,
dashboard, and backtest code must consume these results rather than duplicate
strategy calculations.

Sweep V2 is implemented from the locked rules. TrendPulse uses the recovered
historical indicator conditions where they are established; unresolved
contract details such as final entry/SL/TP and freshness are intentionally
owned by later layers rather than invented here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

Signal = Literal["BUY", "SELL", "NEUTRAL", "NO_SIGNAL"]


@dataclass(frozen=True)
class StrategySignal:
    strategy: str
    signal: Signal
    timestamp: pd.Timestamp
    reason: str


def sweep_v2(
    previous: pd.Series,
    current: pd.Series,
    *,
    timestamp: pd.Timestamp,
) -> StrategySignal:
    """Evaluate one completed Sweep V2 candle against its predecessor."""
    required = {"high", "low", "close"}
    missing = required.difference(previous.index).union(required.difference(current.index))
    if missing:
        raise ValueError(f"Missing Sweep OHLC fields: {sorted(missing)}")
    if timestamp.tzinfo is None:
        raise ValueError("Sweep timestamp must be timezone-aware")

    both_sides = current["high"] > previous["high"] and current["low"] < previous["low"]
    if not both_sides:
        return StrategySignal("Sweep V2", "NO_SIGNAL", timestamp, "BOTH_SIDES_NOT_SWEPT")

    if current["close"] > previous["high"]:
        return StrategySignal("Sweep V2", "BUY", timestamp, "CLOSE_ABOVE_PREVIOUS_HIGH")
    if current["close"] < previous["low"]:
        return StrategySignal("Sweep V2", "SELL", timestamp, "CLOSE_BELOW_PREVIOUS_LOW")
    return StrategySignal("Sweep V2", "NEUTRAL", timestamp, "CLOSE_INSIDE_PREVIOUS_RANGE")


def trendpulse(
    close_1h: pd.Series,
    close_4h: pd.Series,
    *,
    timestamp: pd.Timestamp,
) -> StrategySignal:
    """Evaluate the recovered historical TrendPulse indicator conditions."""
    if timestamp.tzinfo is None:
        raise ValueError("TrendPulse timestamp must be timezone-aware")
    if len(close_1h) < 50 or len(close_4h) < 50:
        return StrategySignal("TrendPulse", "NO_SIGNAL", timestamp, "INSUFFICIENT_DATA")

    ema20 = close_1h.ewm(span=20, adjust=False).mean()
    delta = close_1h.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))

    ema12 = close_1h.ewm(span=12, adjust=False).mean()
    ema26 = close_1h.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()

    ema50_4h = close_4h.ewm(span=50, adjust=False).mean()

    current_1h = close_1h.iloc[-1]
    current_4h = close_4h.iloc[-1]
    current_ema20 = ema20.iloc[-1]
    current_rsi = rsi.iloc[-1]
    current_macd = macd.iloc[-1]
    current_macd_signal = macd_signal.iloc[-1]
    previous_macd = macd.iloc[-2]
    previous_macd_signal = macd_signal.iloc[-2]
    current_ema50_4h = ema50_4h.iloc[-1]

    values = [
        current_ema20,
        current_rsi,
        current_macd,
        current_macd_signal,
        previous_macd,
        previous_macd_signal,
        current_ema50_4h,
    ]
    if any(pd.isna(value) for value in values):
        return StrategySignal("TrendPulse", "NO_SIGNAL", timestamp, "INDICATOR_DATA_UNAVAILABLE")

    bullish = (
        current_4h > current_ema50_4h
        and previous_macd <= previous_macd_signal
        and current_macd > current_macd_signal
        and 50 < current_rsi < 80
        and current_1h > current_ema20
    )
    bearish = (
        current_4h < current_ema50_4h
        and previous_macd >= previous_macd_signal
        and current_macd < current_macd_signal
        and 20 < current_rsi < 50
        and current_1h < current_ema20
    )

    if bullish:
        return StrategySignal("TrendPulse", "BUY", timestamp, "BULLISH_CONFIRMATION")
    if bearish:
        return StrategySignal("TrendPulse", "SELL", timestamp, "BEARISH_CONFIRMATION")
    return StrategySignal("TrendPulse", "NO_SIGNAL", timestamp, "CONDITIONS_NOT_ALIGNED")
