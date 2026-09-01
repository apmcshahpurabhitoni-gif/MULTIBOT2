"""Canonical strategy boundary for MULTIBOT2.

Rules:
- Strategy logic lives only in this module.
- Strategies consume completed candles.
- Strategies never fetch market data.
- Strategies never send Telegram messages.
- Strategies never calculate position sizing.
- Unapproved strategy rules fail closed.
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
    """Canonical strategy result."""

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


def _validate_candle(
    candle: pd.Series,
    *,
    name: str,
) -> None:
    """Validate the fields required by a strategy."""

    required = (
        "open",
        "high",
        "low",
        "close",
    )

    missing = [
        column
        for column in required
        if column not in candle.index
    ]

    if missing:
        raise ValueError(
            f"{name} candle missing: "
            + ", ".join(missing)
        )

    values = [
        candle[column]
        for column in required
    ]

    if any(pd.isna(value) for value in values):
        raise ValueError(
            f"{name} candle contains missing OHLC data"
        )


# ============================================================
# SWEEP V2
# ============================================================

def sweep_v2(
    previous: pd.Series,
    current: pd.Series,
    *,
    timestamp: pd.Timestamp,
) -> StrategySignal:
    """Evaluate the locked Sweep V2 rule.

    BUY:
        Both previous high and previous low are swept,
        and the current close is above the previous high.

    SELL:
        Both previous high and previous low are swept,
        and the current close is below the previous low.

    NEUTRAL:
        Both sides are swept, but the close remains inside
        the previous range.

    NO_SIGNAL:
        Both sides are not swept.

    A one-sided sweep is never converted into BUY or SELL.
    """

    _validate_candle(
        previous,
        name="Previous",
    )

    _validate_candle(
        current,
        name="Current",
    )

    timestamp = pd.Timestamp(timestamp)

    if timestamp.tzinfo is None:
        raise ValueError(
            "Strategy signal timestamp must be timezone-aware"
        )

    timestamp = timestamp.tz_convert(
        IST_TIMEZONE
    )

    previous_high = float(
        previous["high"]
    )

    previous_low = float(
        previous["low"]
    )

    current_high = float(
        current["high"]
    )

    current_low = float(
        current["low"]
    )

    current_close = float(
        current["close"]
    )

    both_sides_swept = (
        current_high > previous_high
        and current_low < previous_low
    )

    if not both_sides_swept:
        return StrategySignal(
            strategy="Sweep V2",
            signal="NO_SIGNAL",
            timestamp=timestamp,
            reason="BOTH_SIDES_NOT_SWEPT",
        )

    if current_close > previous_high:
        return StrategySignal(
            strategy="Sweep V2",
            signal="BUY",
            timestamp=timestamp,
            reason=(
                "BOTH_SIDES_SWEPT_"
                "CLOSE_ABOVE_PREVIOUS_HIGH"
            ),
        )

    if current_close < previous_low:
        return StrategySignal(
            strategy="Sweep V2",
            signal="SELL",
            timestamp=timestamp,
            reason=(
                "BOTH_SIDES_SWEPT_"
                "CLOSE_BELOW_PREVIOUS_LOW"
            ),
        )

    return StrategySignal(
        strategy="Sweep V2",
        signal="NEUTRAL",
        timestamp=timestamp,
        reason=(
            "BOTH_SIDES_SWEPT_"
            "CLOSE_INSIDE_PREVIOUS_RANGE"
        ),
    )


def sweep_v2_from_frame(
    candles: pd.DataFrame,
) -> StrategySignal:
    """Evaluate Sweep V2 using the latest two completed candles."""

    candles = normalize_index(candles)

    if len(candles) < 2:
        timestamp = (
            candles.index[-1]
            if len(candles)
            else pd.Timestamp.now(
                tz=IST_TIMEZONE
            )
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


# ============================================================
# TRENDPULSE
# ============================================================

def trendpulse(
    close_1h: pd.Series,
    close_4h: pd.Series,
    *,
    timestamp: pd.Timestamp,
) -> StrategySignal:
    """TrendPulse strategy boundary.

    The exact approved TrendPulse formula has not yet been
    verified in this clean-slate rebuild.

    Therefore this function intentionally fails closed with
    NO_SIGNAL instead of implementing guessed rules.
    """

    timestamp = pd.Timestamp(timestamp)

    if timestamp.tzinfo is None:
        raise ValueError(
            "TrendPulse timestamp must be timezone-aware"
        )

    timestamp = timestamp.tz_convert(
        IST_TIMEZONE
    )

    return StrategySignal(
        strategy="TrendPulse",
        signal="NO_SIGNAL",
        timestamp=timestamp,
        reason="TREND_PULSE_RULES_NOT_YET_VERIFIED",
    )
