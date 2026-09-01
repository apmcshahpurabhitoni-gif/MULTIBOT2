"""Dashboard data boundary for MULTIBOT2.

The dashboard is presentation-only. Strategy calculations, market-data
fetching, Telegram formatting and risk calculations stay in their own modules.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable

from strategies import StrategySignal
from trading import PaperTrade


def signal_to_dict(signal: StrategySignal) -> dict[str, Any]:
    """Convert a canonical strategy signal into dashboard data."""

    return {
        "strategy": signal.strategy,
        "signal": signal.signal,
        "timestamp": signal.timestamp.isoformat(),
        "reason": signal.reason,
    }


def trade_to_dict(trade: PaperTrade) -> dict[str, Any]:
    """Convert a paper trade into dashboard-safe data."""

    plan = trade.plan

    return {
        "status": trade.status,
        "plan": {
            "strategy": plan.strategy,
            "side": plan.side,
            "signal_timestamp": plan.signal_timestamp.isoformat(),
            "entry": plan.entry,
            "stop_loss": plan.stop_loss,
            "take_profit": plan.take_profit,
            "risk_per_unit": plan.risk_per_unit,
        },
        "exit_price": trade.exit_price,
        "exit_timestamp": (
            trade.exit_timestamp.isoformat()
            if trade.exit_timestamp is not None
            else None
        ),
        "exit_reason": trade.exit_reason,
    }


def build_dashboard_snapshot(
    signals: Iterable[StrategySignal] = (),
    trades: Iterable[PaperTrade] = (),
) -> dict[str, Any]:
    """Build the canonical dashboard payload."""

    signal_rows = [
        signal_to_dict(signal)
        for signal in signals
    ]

    trade_rows = [
        trade_to_dict(trade)
        for trade in trades
    ]

    open_trades = [
        trade
        for trade in trade_rows
        if trade["status"] == "OPEN"
    ]

    return {
        "system": {
            "status": "ONLINE",
            "mode": "PAPER",
        },
        "signals": signal_rows,
        "trades": trade_rows,
        "counts": {
            "signals": len(signal_rows),
            "trades": len(trade_rows),
            "open_trades": len(open_trades),
        },
    }


def empty_dashboard_snapshot() -> dict[str, Any]:
    """Return a valid empty dashboard state."""

    return build_dashboard_snapshot()
