"""Paper-trading execution model for MULTIBOT2.

This module converts approved strategy signals into paper-trade plans.

It does NOT:
- fetch market data
- calculate strategy signals
- send Telegram messages
- determine account risk
- determine position size
- use leverage
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

import pandas as pd

from strategies import StrategySignal


TradeSide = Literal["BUY", "SELL"]
TradeStatus = Literal["OPEN", "CLOSED"]


@dataclass(frozen=True)
class TradePlan:
    """Canonical paper-trade plan."""

    strategy: str
    side: TradeSide
    signal_timestamp: pd.Timestamp

    entry: float
    stop_loss: float
    take_profit: float

    @property
    def risk_per_unit(self) -> float:
        """Absolute price risk for one unit."""

        return abs(self.entry - self.stop_loss)


@dataclass(frozen=True)
class PaperTrade:
    """Canonical paper trade."""

    plan: TradePlan
    status: TradeStatus = "OPEN"

    exit_price: float | None = None
    exit_timestamp: pd.Timestamp | None = None
    exit_reason: str | None = None


def signal_freshness(
    signal_timestamp: pd.Timestamp,
    now: pd.Timestamp,
    *,
    freshness_hours: int = 1,
) -> Literal["FRESH", "STALE"]:
    """Classify signal freshness using the canonical one-hour boundary."""

    signal_timestamp = pd.Timestamp(signal_timestamp)
    now = pd.Timestamp(now)

    if signal_timestamp.tzinfo is None:
        raise ValueError(
            "Signal timestamp must be timezone-aware"
        )

    if now.tzinfo is None:
        raise ValueError(
            "Current timestamp must be timezone-aware"
        )

    if freshness_hours <= 0:
        raise ValueError(
            "freshness_hours must be greater than zero"
        )

    signal_timestamp = signal_timestamp.tz_convert(
        "Asia/Kolkata"
    )

    now = now.tz_convert(
        "Asia/Kolkata"
    )

    age = now - signal_timestamp

    if age < timedelta(0):
        raise ValueError(
            "Signal timestamp cannot be in the future"
        )

    return (
        "FRESH"
        if age <= timedelta(hours=freshness_hours)
        else "STALE"
    )


def make_sweep_trade_plan(
    signal: StrategySignal,
    *,
    entry: float,
    signal_high: float,
    signal_low: float,
) -> TradePlan | None:
    """Create the canonical Sweep V2 paper-trade plan.

    BUY:
        SL = signal low
        TP = Entry + 2R

    SELL:
        SL = signal high
        TP = Entry - 2R

    Position sizing is intentionally not performed here.
    """

    if signal.strategy != "Sweep V2":
        raise ValueError(
            "Sweep trade plans require a Sweep V2 signal"
        )

    if signal.signal not in {"BUY", "SELL"}:
        return None

    entry = float(entry)
    signal_high = float(signal_high)
    signal_low = float(signal_low)

    if entry <= 0:
        raise ValueError("Entry must be positive")

    if signal_high <= 0 or signal_low <= 0:
        raise ValueError(
            "Signal high/low must be positive"
        )

    if signal_low >= signal_high:
        raise ValueError(
            "Signal low must be below signal high"
        )

    if signal.signal == "BUY":
        stop_loss = signal_low
        risk = entry - stop_loss

        if risk <= 0:
            raise ValueError(
                "BUY entry must be above stop-loss"
            )

        take_profit = entry + (2 * risk)

        side: TradeSide = "BUY"

    else:
        stop_loss = signal_high
        risk = stop_loss - entry

        if risk <= 0:
            raise ValueError(
                "SELL entry must be below stop-loss"
            )

        take_profit = entry - (2 * risk)

        side = "SELL"

    return TradePlan(
        strategy=signal.strategy,
        side=side,
        signal_timestamp=signal.timestamp,
        entry=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
    )


def close_trade(
    trade: PaperTrade,
    *,
    exit_price: float,
    exit_timestamp: pd.Timestamp,
    exit_reason: str,
) -> PaperTrade:
    """Return a closed copy of a paper trade."""

    if trade.status == "CLOSED":
        raise ValueError(
            "Trade is already closed"
        )

    exit_timestamp = pd.Timestamp(exit_timestamp)

    if exit_timestamp.tzinfo is None:
        raise ValueError(
            "Exit timestamp must be timezone-aware"
        )

    exit_price = float(exit_price)

    if exit_price <= 0:
        raise ValueError(
            "Exit price must be positive"
        )

    if not exit_reason.strip():
        raise ValueError(
            "Exit reason cannot be empty"
        )

    return PaperTrade(
        plan=trade.plan,
        status="CLOSED",
        exit_price=exit_price,
        exit_timestamp=exit_timestamp.tz_convert(
            "Asia/Kolkata"
        ),
        exit_reason=exit_reason.strip(),
    )
