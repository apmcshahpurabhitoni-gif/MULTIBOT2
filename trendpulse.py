"""TrendPulse strategy core for MULTIBOT2.

This module contains only the historical, source-derived TrendPulse calculation
that has been approved as the reconstruction baseline. It deliberately does not
contain Telegram, dashboard, database, provider, or paper-trading side effects.

IMPORTANT:
The historical baseline does not establish the final entry, stop-loss,
take-profit, repeated-signal, or complete market-universe contract. Those parts
remain unresolved and are therefore not guessed here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

Trend = Literal["BULLISH", "BEARISH", "NO_SIGNAL"]


@dataclass(frozen=True)
class TrendPulseResult:
    """Deterministic TrendPulse calculation result."""

    trend: Trend
    reason: str
    atr_percent: float | None = None


# Historical parameters recovered from the legacy TrendPulse implementation.
EMA_FAST_1H = 20
EMA_TREND_4H = 50
RSI_PERIOD = 14
ATR_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
MIN_1H_ROWS = 50
MIN_4H_ROWS = 15
MIN_ATR_PERCENT = 0.2


def _validate_ohlc(frame: pd.DataFrame) -> None:
    required = {"open", "high", "low", "close"}
    missing = required.difference(frame.columns.str.lower())
    if missing:
        raise ValueError(f"Missing required OHLC columns: {sorted(missing)}")


def _rsi(close: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def _atr(frame: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def _macd(close: pd.Series) -> tuple[pd.Series, pd.Series]:
    fast = close.ewm(span=MACD_FAST, adjust=False).mean()
    slow = close.ewm(span=MACD_SLOW, adjust=False).mean()
    line = fast - slow
    signal = line.ewm(span=MACD_SIGNAL, adjust=False).mean()
    return line, signal


def _resample_4h(frame_1h: pd.DataFrame) -> pd.DataFrame:
    """Build the historical 4H view from 1H data.

    The historical implementation derived its 4H view from 1H input. Session
    alignment is intentionally not imposed here; the canonical market/session
    layer will own boundary construction once that contract is frozen.
    """

    frame = frame_1h.copy()
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError("TrendPulse input must use a DatetimeIndex")
    if frame.index.tz is None:
        raise ValueError("TrendPulse input index must be timezone-aware")

    return (
        frame[["open", "high", "low", "close"]]
        .resample("4h")
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
            }
        )
        .dropna()
    )


def evaluate_trendpulse(frame_1h: pd.DataFrame) -> TrendPulseResult:
    """Evaluate the recovered historical TrendPulse baseline.

    The supplied dataframe must contain at least 50 completed 1H rows and use
    timezone-aware timestamps. The caller is responsible for ensuring that the
    final row is the latest completed candle; this function never invents a
    completion state.
    """

    if len(frame_1h) < MIN_1H_ROWS:
        return TrendPulseResult("NO_SIGNAL", "INSUFFICIENT_1H_DATA")

    frame = frame_1h.copy()
    frame.columns = [str(column).lower() for column in frame.columns]
    _validate_ohlc(frame)
    frame = frame.sort_index()

    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError("TrendPulse input must use a DatetimeIndex")
    if frame.index.tz is None:
        raise ValueError("TrendPulse input index must be timezone-aware")

    frame_4h = _resample_4h(frame)
    if len(frame_4h) < MIN_4H_ROWS:
        return TrendPulseResult("NO_SIGNAL", "INSUFFICIENT_4H_DATA")

    frame["ema20"] = frame["close"].ewm(span=EMA_FAST_1H, adjust=False).mean()
    frame["rsi14"] = _rsi(frame["close"])
    frame["atr14"] = _atr(frame)
    frame["macd"], frame["macd_signal"] = _macd(frame["close"])

    frame_4h["ema50"] = frame_4h["close"].ewm(
        span=EMA_TREND_4H, adjust=False
    ).mean()
    frame_4h["atr14"] = _atr(frame_4h)

    # Historical code evaluates the last closed row, not the still-forming row.
    current_1h = frame.iloc[-2]
    previous_1h = frame.iloc[-3]
    current_4h = frame_4h.iloc[-2]

    atr_percent = float(current_4h["atr14"] / current_4h["close"] * 100)
    if atr_percent < MIN_ATR_PERCENT:
        return TrendPulseResult("NO_SIGNAL", "LOW_ATR_PERCENT", atr_percent)

    bullish = (
        current_4h["close"] > current_4h["ema50"]
        and previous_1h["macd"] <= previous_1h["macd_signal"]
        and current_1h["macd"] > current_1h["macd_signal"]
        and current_1h["rsi14"] > 50
        and current_1h["rsi14"] < 80
        and current_1h["close"] > current_1h["ema20"]
    )

    bearish = (
        current_4h["close"] < current_4h["ema50"]
        and previous_1h["macd"] >= previous_1h["macd_signal"]
        and current_1h["macd"] < current_1h["macd_signal"]
        and current_1h["rsi14"] < 50
        and current_1h["rsi14"] > 20
        and current_1h["close"] < current_1h["ema20"]
    )

    if bullish:
        return TrendPulseResult("BULLISH", "HISTORICAL_BULLISH_RULES", atr_percent)
    if bearish:
        return TrendPulseResult("BEARISH", "HISTORICAL_BEARISH_RULES", atr_percent)
    return TrendPulseResult("NO_SIGNAL", "CONDITIONS_NOT_MET", atr_percent)
