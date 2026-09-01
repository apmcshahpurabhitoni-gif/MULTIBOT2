"""Canonical strategy engine for MULTIBOT2.

Strategy calculations live here only.

Important:
- Strategies consume completed candles.
- Strategies do not fetch market data.
- Strategies do not send Telegram messages.
- Strategies do not calculate position sizing.
- Strategies do not contain dashboard/UI code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from candles import normalize_index
from config import IST_TIMEZONE


SignalType = Literal[
    "BUY",
    "SELL",
    "NEUTRAL",
    "NO_SIGNAL",
]


@dataclass(frozen=True)
class StrategySignal:
    """Canonical result returned by every strategy."""

    strategy: str
    signal: SignalType
    timestamp: pd.Timestamp
    reason: str

    def __post_init__(self) -> None:
        timestamp = pd.Timestamp(self.timestamp)

        if timestamp.tzinfo is None:
            raise ValueError(
                "Strategy signal timestamp must be timezone-aware"
            )

        object.__setattr__(
            self,
            "timestamp",
            timestamp.tz_convert(IST_TIMEZONE),
        )


def _require_columns(
    frame: pd.DataFrame,
    columns: tuple[str, ...],
) -> None:
    missing = [
        column
        for column in columns
        if column not in frame.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {', '.join(missing)}"
        )


def sweep_v2(
    previous: pd.Series,
    current: pd.Series,
    *,
    timestamp: pd.Timestamp,
) -> StrategySignal:
    """Evaluate one completed Sweep V2 candle.

    Rules:
    1. The current candle must sweep both the previous high and previous low.
    2. Close above the previous high -> BUY.
    3. Close below the previous low -> SELL.
    4. Close inside the previous range -> NEUTRAL.
    5. If both sides were not swept -> NO_SIGNAL.

    No one-sided sweep is treated as a trade signal.
    """

    required = ("high", "low", "close")

    for name, candle in (
        ("previous", previous),
        ("current", current),
    ):
        missing = [
            column
            for column in required
            if column not in candle.index
        ]

        if missing:
            raise ValueError(
                f"{name} candle missing: {', '.join(missing)}"
            )

    timestamp = pd.Timestamp(timestamp)

    if timestamp.tzinfo is None:
        raise ValueError(
            "Strategy signal timestamp must be timezone-aware"
        )

    timestamp = timestamp.tz_convert(IST_TIMEZONE)

    previous_high = float(previous["high"])
    previous_low = float(previous["low"])
    current_high = float(current["high"])
    current_low = float(current["low"])
    current_close = float(current["close"])

    if current_high > previous_high and current_low < previous_low:
        if current_close > previous_high:
            return StrategySignal(
                strategy="Sweep V2",
                signal="BUY",
                timestamp=timestamp,
                reason="BOTH_SIDES_SWEPT_CLOSE_ABOVE_PREVIOUS_HIGH",
            )

        if current_close < previous_low:
            return StrategySignal(
                strategy="Sweep V2",
                signal="SELL",
                timestamp=timestamp,
                reason="BOTH_SIDES_SWEPT_CLOSE_BELOW_PREVIOUS_LOW",
            )

        return StrategySignal(
            strategy="Sweep V2",
            signal="NEUTRAL",
            timestamp=timestamp,
            reason="BOTH_SIDES_SWEPT_CLOSE_INSIDE_PREVIOUS_RANGE",
        )

    return StrategySignal(
        strategy="Sweep V2",
        signal="NO_SIGNAL",
        timestamp=timestamp,
        reason="BOTH_SIDES_NOT_SWEPT",
    )


def sweep_v2_from_frame(
    candles: pd.DataFrame,
) -> StrategySignal:
    """Evaluate the most recent completed pair of Sweep candles."""

    candles = normalize_index(candles)

    _require_columns(
        candles,
        ("open", "high", "low", "close"),
    )

    if len(candles) < 2:
        timestamp = candles.index[-1] if len(candles) else pd.Timestamp.now(
            tz=IST_TIMEZONE
        )

        return StrategySignal(
            strategy="Sweep V2",
            signal="NO_SIGNAL",
            timestamp=timestamp,
            reason="INSUFFICIENT_DATA",
        )

    previous = candles.iloc[-2]
    current = candles.iloc[-1]

    return sweep_v2(
        previous,
        current,
        timestamp=candles.index[-1],
    )


def _ema(
    series: pd.Series,
    period: int,
) -> pd.Series:
    return series.ewm(
        span=period,
        adjust=False,
        min_periods=period,
    ).mean()


def _rsi(
    series: pd.Series,
    period: int = 14,
) -> pd.Series:
    delta = series.diff()

    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    average_gain = gains.rolling(
        period,
        min_periods=period,
    ).mean()

    average_loss = losses.rolling(
        period,
        min_periods=period,
    ).mean()

    relative_strength = average_gain / average_loss.replace(
        0,
        pd.NA,
    )

    return 100 - (
        100 / (1 + relative_strength)
    )


def trendpulse(
    close_1h: pd.Series,
    close_4h: pd.Series,
    *,
    timestamp: pd.Timestamp,
) -> StrategySignal:
    """Evaluate the recovered TrendPulse indicator boundary.

    This function intentionally contains only the recovered indicator
    conditions. Entry, SL, TP, freshness, repeated-signal handling and
    provider behavior belong to their respective layers.
    """

    timestamp = pd.Timestamp(timestamp)

    if timestamp.tzinfo is None:
        raise ValueError(
            "TrendPulse timestamp must be timezone-aware"
        )

    timestamp = timestamp.tz_convert(IST_TIMEZONE)

    if len(close_1h) < 50 or len(close_4h) < 50:
        return StrategySignal(
            strategy="TrendPulse",
            signal="NO_SIGNAL",
            timestamp=timestamp,
            reason="INSUFFICIENT_DATA",
        )

    close_1h = pd.Series(close_1h, dtype=float).copy()
    close_4h = pd.Series(close_4h, dtype=float).copy()

    ema20 = _ema(close_1h, 20)

    rsi = _rsi(
        close_1h,
        14,
    )

    ema12 = _ema(
        close_1h,
        12,
    )

    ema26 = _ema(
        close_1h,
        26,
    )

    macd = ema12 - ema26

    macd_signal = _ema(
        macd,
        9,
    )

    ema50_4h = _ema(
        close_4h,
        50,
    )

    required_values = (
        ema20.iloc[-1],
        rsi.iloc[-1],
        macd.iloc[-1],
        macd_signal.iloc[-1],
        macd.iloc[-2],
        macd_signal.iloc[-2],
        ema50_4h.iloc[-1],
    )

    if any(pd.isna(value) for value in required_values):
        return StrategySignal(
            strategy="TrendPulse",
            signal="NO_SIGNAL",
            timestamp=timestamp,
            reason="INDICATOR_DATA_UNAVAILABLE",
        )

    price_1h = float(close_1h.iloc[-1])
    price_4h = float(close_4h.iloc[-1])

    current_ema20 = float(ema20.iloc[-1])
    current_rsi = float(rsi.iloc[-1])

    current_macd = float(macd.iloc[-1])
    previous_macd = float(macd.iloc[-2])

    current_macd_signal = float(
        macd_signal.iloc[-1]
    )

    previous_macd_signal = float(
        macd_signal.iloc[-2]
    )

    current_ema50_4h = float(
        ema50_4h.iloc[-1]
    )

    bullish = (
        price_4h > current_ema50_4h
        and previous_macd <= previous_macd_signal
        and current_macd > current_macd_signal
        and 50 < current_rsi < 80
        and price_1h > current_ema20
    )

    bearish = (
        price_4h < current_ema50_4h
        and previous_macd >= previous_macd_signal
        and current_macd < current_macd_signal
        and 20 < current_rsi < 50
        and price_1h < current_ema20
    )

    if bullish:
        return StrategySignal(
            strategy="TrendPulse",
            signal="BUY",
            timestamp=timestamp,
            reason="BULLISH_CONFIRMATION",
        )

    if bearish:
        return StrategySignal(
            strategy="TrendPulse",
            signal="SELL",
            timestamp=timestamp,
            reason="BEARISH_CONFIRMATION",
        )

    return StrategySignal(
        strategy="TrendPulse",
        signal="NO_SIGNAL",
        timestamp=timestamp,
        reason="CONDITIONS_NOT_ALIGNED",
    )
