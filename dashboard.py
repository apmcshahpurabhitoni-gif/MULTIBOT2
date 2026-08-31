"""Dashboard backend boundary for MULTIBOT2.

The dashboard consumes canonical strategy/trading data. It does not calculate
signals, entries, stops, targets, or risk rules. The implementation is kept
small so the UI can be built independently in the next files.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable

from strategies import StrategySignal
from trading import PaperTrade


def signal_view(signal: StrategySignal) -> dict[str, Any]:
    """Convert a canonical signal into dashboard-safe display data."""
    return {
        "strategy": signal.strategy,
        "signal": signal.signal,
        "timestamp": signal.timestamp.isoformat(),
        "reason": signal.reason,
    }


def trade_view(trade: PaperTrade) -> dict[str, Any]:
    """Convert a paper trade into dashboard-safe display data."""
    result = asdict(trade)
    result["plan"]["signal_timestamp"] = trade.plan.signal_timestamp.isoformat()
    return result


def build_dashboard_snapshot(
    signals: Iterable[StrategySignal] = (),
    trades: Iterable[PaperTrade] = (),
) -> dict[str, Any]:
    """Build the minimal canonical dashboard payload."""
    signal_rows = [signal_view(signal) for signal in signals]
    trade_rows = [trade_view(trade) for trade in trades]
    return {
        "signals": signal_rows,
        "trades": trade_rows,
        "counts": {
            "signals": len(signal_rows),
            "open_trades": sum(1 for trade in trade_rows if trade["status"] == "OPEN"),
        },
    }
