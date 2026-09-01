"""Canonical strategy logic for MULTIBOT2.

Approved TrendPulse rules are implemented here. Strategies consume candle
frames only and never fetch market data, send Telegram messages, or calculate
position sizing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from candles import normalize_index
from config import IST_TIMEZONE

SignalType = Literal["BUY", "SELL", "NEUTRAL", "NO_SIGNAL"]


@dataclass(frozen=True)
class StrategySignal:
    strategy: str
    signal: SignalType
    timestamp: pd.Timestamp
    reason: str
    entry: float | None = None
    atr: float | None = None

    def __post_init__(self) -> None:
        timestamp = pd.Timestamp(self.timestamp)
        if timestamp.tzinfo is None:
            raise ValueError("Strategy signal timestamp must be timezone-aware")
        object.__setattr__(self, "timestamp", timestamp.tz_convert(IST_TIMEZONE))


def _validate_candle(candle: pd.Series, *, name: str) -> None:
    required = ("open", "high", "low", "close")
    missing = [column for column in required if column not in candle.index]
    if missing:
        raise ValueError(f"{name} candle missing: " + ", ".join(missing))
    if any(pd.isna(candle[column]) for column in required):
        raise ValueError(f"{name} candle contains missing OHLC data")


# ============================================================
# SWEEP V2
# ============================================================


def sweep_v2(previous: pd.Series, current: pd.Series, *, timestamp: pd.Timestamp) -> StrategySignal:
    """Locked Sweep V2: both sides must sweep before a directional signal."""
    _validate_candle(previous, name="Previous")
    _validate_candle(current, name="Current")
    timestamp = pd.Timestamp(timestamp)
    if timestamp.tzinfo is None:
        raise ValueError("Strategy signal timestamp must be timezone-aware")
    timestamp = timestamp.tz_convert(IST_TIMEZONE)

    previous_high = float(previous["high"])
    previous_low = float(previous["low"])
    current_high = float(current["high"])
    current_low = float(current["low"])
    current_close = float(current["close"])

    if not (current_high > previous_high and current_low < previous_low):
        return StrategySignal("Sweep V2", "NO_SIGNAL", timestamp, "BOTH_SIDES_NOT_SWEPT")
    if current_close > previous_high:
        return StrategySignal("Sweep V2", "BUY", timestamp, "BOTH_SIDES_SWEPT_CLOSE_ABOVE_PREVIOUS_HIGH")
    if current_close < previous_low:
        return StrategySignal("Sweep V2", "SELL", timestamp, "BOTH_SIDES_SWEPT_CLOSE_BELOW_PREVIOUS_LOW")
    return StrategySignal("Sweep V2", "NEUTRAL", timestamp, "BOTH_SIDES_SWEPT_CLOSE_INSIDE_PREVIOUS_RANGE")


def sweep_v2_from_frame(candles: pd.DataFrame) -> StrategySignal:
    candles = normalize_index(candles)
    if len(candles) < 2:
        timestamp = candles.index[-1] if len(candles) else pd.Timestamp.now(tz=IST_TIMEZONE)
        return StrategySignal("Sweep V2", "NO_SIGNAL", timestamp, "INSUFFICIENT_DATA")
    return sweep_v2(candles.iloc[-2], candles.iloc[-1], timestamp=candles.index[-1])


# ============================================================
# TRENDPULSE INDICATORS
# ============================================================


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, pd.NA)
    result = (100 - (100 / (1 + rs))).astype(float)
    result = result.where(loss.ne(0), 100.0)
    return result.fillna(50.0)


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series]:
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    return macd_line, ema(macd_line, signal)


def atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(period).mean()


def derive_4h_from_1h(candles_1h: pd.DataFrame) -> pd.DataFrame:
    candles_1h = normalize_index(candles_1h)
    if candles_1h.empty:
        return candles_1h.copy()
    return candles_1h[["open", "high", "low", "close"]].resample("4h").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()


# ============================================================
# TRENDPULSE — APPROVED RULES
# ============================================================


def trendpulse_from_frames(
    candles_1h: pd.DataFrame,
    candles_4h: pd.DataFrame | None = None,
) -> StrategySignal:
    """Evaluate the approved TrendPulse rules on completed candle data.

    BUY requires:
      4H close > 4H EMA50
      4H ATR% >= 0.2
      1H MACD bullish crossover
      1H RSI(14) > 50 and < 80
      1H close > 1H EMA20

    SELL requires the exact inverse:
      4H close < 4H EMA50
      4H ATR% >= 0.2
      1H MACD bearish crossover
      1H RSI(14) < 50 and > 20
      1H close < 1H EMA20

    The latest completed 1H candle is the signal candle. If the caller passes
    raw data containing a still-forming final candle, the penultimate candle is
    used, matching the original implementation's completed-candle behavior.
    """
    candles_1h = normalize_index(candles_1h)
    if candles_4h is None:
        candles_4h = derive_4h_from_1h(candles_1h)
    else:
        candles_4h = normalize_index(candles_4h)

    if len(candles_1h) < 50 or len(candles_4h) < 15:
        timestamp = candles_1h.index[-1] if len(candles_1h) else pd.Timestamp.now(tz=IST_TIMEZONE)
        return StrategySignal("TrendPulse", "NO_SIGNAL", timestamp, "INSUFFICIENT_DATA")

    close_1h = candles_1h["close"]
    close_4h = candles_4h["close"]
    ema20 = ema(close_1h, 20)
    rsi14 = rsi(close_1h, 14)
    atr1h = atr(candles_1h, 14)
    macd_line, signal_line = macd(close_1h, 12, 26, 9)
    ema50_4h = ema(close_4h, 50)
    atr14_4h = atr(candles_4h, 14)

    i = len(candles_1h) - 2
    h = len(candles_4h) - 2
    if i < 2 or h < 0:
        return StrategySignal("TrendPulse", "NO_SIGNAL", candles_1h.index[-1], "INSUFFICIENT_CLOSED_CANDLES")

    timestamp = candles_1h.index[i]
    values = {
        "m1_close": float(close_1h.iloc[i]),
        "m1_ema20": float(ema20.iloc[i]),
        "m1_rsi": float(rsi14.iloc[i]),
        "m1_atr": float(atr1h.iloc[i]),
        "macd_previous": float(macd_line.iloc[i - 1]),
        "macd_current": float(macd_line.iloc[i]),
        "signal_previous": float(signal_line.iloc[i - 1]),
        "signal_current": float(signal_line.iloc[i]),
        "htf_close": float(close_4h.iloc[h]),
        "htf_ema50": float(ema50_4h.iloc[h]),
        "htf_atr": float(atr14_4h.iloc[h]),
    }

    if any(pd.isna(value) for value in values.values()):
        return StrategySignal("TrendPulse", "NO_SIGNAL", timestamp, "INDICATOR_DATA_UNAVAILABLE")
    if values["htf_close"] == 0:
        return StrategySignal("TrendPulse", "NO_SIGNAL", timestamp, "INVALID_HTF_CLOSE")

    atr_pct = (values["htf_atr"] / values["htf_close"]) * 100
    if atr_pct < 0.2:
        return StrategySignal("TrendPulse", "NO_SIGNAL", timestamp, "ATR_PERCENT_BELOW_0_2")

    bullish = (
        values["htf_close"] > values["htf_ema50"]
        and values["macd_previous"] <= values["signal_previous"]
        and values["macd_current"] > values["signal_current"]
        and values["m1_rsi"] > 50
        and values["m1_rsi"] < 80
        and values["m1_close"] > values["m1_ema20"]
    )
    if bullish:
        return StrategySignal(
            "TrendPulse", "BUY", timestamp,
            "HTF_BULLISH_MACD_RSI_EMA_ALIGNMENT",
            entry=values["m1_close"], atr=values["m1_atr"],
        )

    bearish = (
        values["htf_close"] < values["htf_ema50"]
        and values["macd_previous"] >= values["signal_previous"]
        and values["macd_current"] < values["signal_current"]
        and values["m1_rsi"] < 50
        and values["m1_rsi"] > 20
        and values["m1_close"] < values["m1_ema20"]
    )
    if bearish:
        return StrategySignal(
            "TrendPulse", "SELL", timestamp,
            "HTF_BEARISH_MACD_RSI_EMA_ALIGNMENT",
            entry=values["m1_close"], atr=values["m1_atr"],
        )

    return StrategySignal("TrendPulse", "NO_SIGNAL", timestamp, "NO_APPROVED_ALIGNMENT")


def calc_sl_tp(signal: StrategySignal) -> tuple[float, float]:
    """Approved hard stops: 1.5 ATR SL and 3.0 ATR TP (1:2 R:R)."""
    if signal.signal not in ("BUY", "SELL"):
        raise ValueError("SL/TP requires a BUY or SELL signal")
    if signal.entry is None or signal.atr is None:
        raise ValueError("TrendPulse signal is missing entry or ATR")

    entry = float(signal.entry)
    atr_value = float(signal.atr)
    if signal.signal == "BUY":
        return entry - atr_value * 1.5, entry + atr_value * 3.0
    return entry + atr_value * 1.5, entry - atr_value * 3.0


def trendpulse(close_1h: pd.Series, close_4h: pd.Series, *, timestamp: pd.Timestamp) -> StrategySignal:
    """Compatibility boundary; full approved rules require OHLC frames for ATR."""
    timestamp = pd.Timestamp(timestamp)
    if timestamp.tzinfo is None:
        raise ValueError("TrendPulse timestamp must be timezone-aware")
    return StrategySignal(
        "TrendPulse", "NO_SIGNAL", timestamp.tz_convert(IST_TIMEZONE),
        "USE_TRENDPULSE_FROM_FRAMES_FOR_FULL_RULES",
    )
