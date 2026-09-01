"""Dashboard data layer for MULTIBOT2.

This module prepares canonical backend data for the dashboard.
It does not calculate strategy signals or modify trading rules.
"""

from __future__ import annotations

from typing import Any, Iterable

from config import (
    ACCOUNT_NAMES,
    ACCOUNT_SIZE_INR,
    ACCOUNT_TRADE_LIMITS,
    LEVERAGE,
    NSE_15_SYMBOLS,
    RISK_PER_TRADE_INR,
)
from strategies import StrategySignal
from trading import AccountState, PaperTrade


def signal_to_dict(
    signal: StrategySignal,
) -> dict[str, Any]:
    """Convert a strategy signal to dashboard-safe data."""

    return {
        "strategy": signal.strategy,
        "signal": signal.signal,
        "timestamp": signal.timestamp.isoformat(),
        "reason": signal.reason,
    }


def trade_to_dict(
    trade: PaperTrade,
) -> dict[str, Any]:
    """Convert a paper trade to dashboard-safe data."""

    plan = trade.plan

    return {
        "status": trade.status,
        "plan": {
            "strategy": plan.strategy,
            "side": plan.side,
            "signal_timestamp": (
                plan.signal_timestamp.isoformat()
            ),
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


def account_to_dict(
    account: AccountState,
) -> dict[str, Any]:
    """Convert account state to dashboard-safe data."""

    daily_limit = account.daily_trade_limit

    return {
        "name": account.name,
        "starting_balance": account.starting_balance,
        "planned_risk_used": account.planned_risk_used,
        "daily_trade_limit": daily_limit,
        "max_daily_planned_risk": account.max_daily_planned_risk,
        "trades_today": account.trades_today,
        "remaining_trades": max(
            0,
            daily_limit - account.trades_today,
        ),
        "remaining_planned_risk": max(
            0,
            account.max_daily_planned_risk
            - account.planned_risk_used,
        ),
    }


def build_dashboard_snapshot(
    signals: Iterable[StrategySignal] = (),
    trades: Iterable[PaperTrade] = (),
    accounts: Iterable[AccountState] = (),
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

    account_rows = [
        account_to_dict(account)
        for account in accounts
    ]

    open_trades = [
        trade
        for trade in trade_rows
        if trade["status"] == "OPEN"
    ]

    closed_trades = [
        trade
        for trade in trade_rows
        if trade["status"] == "CLOSED"
    ]

    return {
        "system": {
            "status": "ONLINE",
            "mode": "PAPER",
            "timezone": "Asia/Kolkata",
            "timeframe": "1h",
            "leverage": LEVERAGE,
        },

        "rules": {
            "account_size_inr": ACCOUNT_SIZE_INR,
            "risk_per_trade_inr": RISK_PER_TRADE_INR,
            "account_trade_limits": dict(ACCOUNT_TRADE_LIMITS),
        },

        "universe": {
            "count": len(NSE_15_SYMBOLS),
            "symbols": list(NSE_15_SYMBOLS),
            "fixed": True,
        },

        "accounts": {
            "count": len(ACCOUNT_NAMES),
            "names": list(ACCOUNT_NAMES),
            "data": account_rows,
        },

        "signals": signal_rows,

        "trades": trade_rows,

        "counts": {
            "signals": len(signal_rows),
            "trades": len(trade_rows),
            "open_trades": len(open_trades),
            "closed_trades": len(closed_trades),
        },
    }


def empty_dashboard_snapshot() -> dict[str, Any]:
    """Return a valid empty dashboard state."""

    return build_dashboard_snapshot()
