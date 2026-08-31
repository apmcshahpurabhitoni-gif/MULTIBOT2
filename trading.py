"""Paper-trading primitives for MULTIBOT2.

This module consumes canonical strategy signals. It does not calculate Sweep
or TrendPulse conditions and does not invent unresolved account/risk rules.
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
    strategy: str
    side: TradeSide
    signal_timestamp: pd.Timestamp
    entry: float
    stop_loss: float
    take_profit: float


@dataclass(frozen=True)
class PaperTrade:
    plan: TradePlan
    status: TradeStatus = "OPEN"
    exit_price: float | None = None
    exit_timestamp: pd.Timestamp | None = None
    exit_reason: str | None = None


def freshness(signal_timestamp: pd.Timestamp, now: pd.Timestamp) -> str:
    """Return the locked one-hour freshness classification."""
    if signal_timestamp.tzinfo is None or now.tzinfo is None:
        raise ValueError("Freshness timestamps must be timezone-aware")
    age = now - signal_timestamp
    if age < timedelta(0):
        raise ValueError("Signal timestamp cannot be in the future")
    return "FRESH" if age <= timedelta(hours=1) else "STALE"


def make_sweep_trade_plan(
    signal: StrategySignal,
    *,
    entry: float,
    signal_high: float,
    signal_low: float,
) -> TradePlan | None:
    """Create the locked Sweep V2 2R paper-trade plan.

    Entry is supplied by the execution/data layer. SL uses the signal candle
    extreme and TP is calculated at 2R. No position sizing or account-risk
    assumptions are made.
    """
    if signal.signal not in {"BUY", "SELL"}:
        return None
    if entry <= 0 or signal_high <= 0 or signal_low <= 0:
        raise ValueError("Trade prices must be positive")

    if signal.signal == "BUY":
        stop_loss = signal_low
        risk = entry - stop_loss
        if risk <= 0:
            raise ValueError("BUY entry must be above signal low")
        take_profit = entry + (2 * risk)
        side: TradeSide = "BUY"
    else:
        stop_loss = signal_high
        risk = stop_loss - entry
        if risk <= 0:
            raise ValueError("SELL entry must be below signal high")
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
