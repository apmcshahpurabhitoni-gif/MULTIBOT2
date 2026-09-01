"""Paper-trading and risk rules for MULTIBOT2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

import pandas as pd

from config import (
    ACCOUNT_SIZE_INR,
    ACCOUNT_TRADE_LIMITS,
    LEVERAGE,
    RISK_PER_TRADE_INR,
)
from strategies import StrategySignal


TradeSide = Literal["BUY", "SELL"]
TradeStatus = Literal["OPEN", "CLOSED"]


class TradingRuleError(ValueError):
    """Raised when a paper-trading rule is violated."""


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
        return abs(
            self.entry - self.stop_loss
        )


@dataclass(frozen=True)
class PaperTrade:
    """Canonical paper trade."""

    plan: TradePlan

    status: TradeStatus = "OPEN"

    exit_price: float | None = None
    exit_timestamp: pd.Timestamp | None = None
    exit_reason: str | None = None


@dataclass(frozen=True)
class AccountState:
    """Paper-account state."""

    name: str
    starting_balance: float = ACCOUNT_SIZE_INR
    planned_risk_used: float = 0.0
    trades_today: int = 0

    @property
    def daily_trade_limit(self) -> int:
        """Return the original daily limit for this logical account."""
        try:
            return ACCOUNT_TRADE_LIMITS[self.name.lower()]
        except KeyError as exc:
            raise TradingRuleError(
                f"Unknown trading account: {self.name}"
            ) from exc

    @property
    def max_daily_planned_risk(self) -> float:
        """Return this account's total planned-risk allowance."""
        return RISK_PER_TRADE_INR * self.daily_trade_limit



def validate_risk_configuration() -> None:
    """Validate the frozen risk and original account-limit rules."""

    if ACCOUNT_SIZE_INR != 100_000:
        raise TradingRuleError(
            "Account size must be ₹100,000"
        )

    if RISK_PER_TRADE_INR != 2_000:
        raise TradingRuleError(
            "Risk per trade must be ₹2,000"
        )

    expected_limits = {
        "macro": 20,
        "nifty": 5,
        "ny_session": 3,
        "sweep_4h": 3,
    }
    if ACCOUNT_TRADE_LIMITS != expected_limits:
        raise TradingRuleError(
            "Per-account trade limits do not match the original MULTIBOT rules"
        )

    if LEVERAGE != 1.0:
        raise TradingRuleError(
            "MULTIBOT2 uses 1x leverage"
        )



def signal_freshness(
    signal_timestamp: pd.Timestamp,
    now: pd.Timestamp,
    *,
    freshness_hours: int = 1,
) -> Literal["FRESH", "STALE"]:
    """Classify signal freshness.

    A signal is FRESH when its age is <= 1 hour.
    """

    signal_timestamp = pd.Timestamp(
        signal_timestamp
    )

    now = pd.Timestamp(now)

    if signal_timestamp.tzinfo is None:
        raise TradingRuleError(
            "Signal timestamp must be timezone-aware"
        )

    if now.tzinfo is None:
        raise TradingRuleError(
            "Current timestamp must be timezone-aware"
        )

    if freshness_hours <= 0:
        raise TradingRuleError(
            "Freshness period must be positive"
        )

    signal_timestamp = signal_timestamp.tz_convert(
        "Asia/Kolkata"
    )

    now = now.tz_convert(
        "Asia/Kolkata"
    )

    age = now - signal_timestamp

    if age < timedelta(0):
        raise TradingRuleError(
            "Signal timestamp cannot be in the future"
        )

    if age <= timedelta(
        hours=freshness_hours
    ):
        return "FRESH"

    return "STALE"



def can_open_trade(
    account: AccountState,
) -> bool:
    """Return whether another trade may be opened today for this account.

    The original bot used independent account limits:
    Macro=20, Nifty=5, NY Session=3, Sweep 4H=3.
    """

    validate_risk_configuration()

    daily_limit = account.daily_trade_limit

    if account.trades_today >= daily_limit:
        return False

    if (
        account.planned_risk_used
        + RISK_PER_TRADE_INR
        > account.max_daily_planned_risk
    ):
        return False

    return True



def make_sweep_trade_plan(
    signal: StrategySignal,
    *,
    entry: float,
    signal_high: float,
    signal_low: float,
) -> TradePlan | None:
    """Create the Sweep V2 trade plan.

    BUY:
        SL = signal low
        TP = Entry + 2R

    SELL:
        SL = signal high
        TP = Entry - 2R

    Position size is deliberately not calculated here because
    execution sizing depends on the approved instrument contract.
    """

    validate_risk_configuration()

    if signal.strategy != "Sweep V2":
        raise TradingRuleError(
            "Sweep trade plan requires Sweep V2"
        )

    if signal.signal not in {
        "BUY",
        "SELL",
    }:
        return None

    entry = float(entry)

    signal_high = float(
        signal_high
    )

    signal_low = float(
        signal_low
    )

    if entry <= 0:
        raise TradingRuleError(
            "Entry must be positive"
        )

    if signal_low <= 0:
        raise TradingRuleError(
            "Signal low must be positive"
        )

    if signal_high <= 0:
        raise TradingRuleError(
            "Signal high must be positive"
        )

    if signal_low >= signal_high:
        raise TradingRuleError(
            "Signal low must be below signal high"
        )

    if signal.signal == "BUY":

        stop_loss = signal_low

        risk = (
            entry
            - stop_loss
        )

        if risk <= 0:
            raise TradingRuleError(
                "BUY entry must be above stop-loss"
            )

        take_profit = (
            entry
            + (2 * risk)
        )

        side: TradeSide = "BUY"

    else:

        stop_loss = signal_high

        risk = (
            stop_loss
            - entry
        )

        if risk <= 0:
            raise TradingRuleError(
                "SELL entry must be below stop-loss"
            )

        take_profit = (
            entry
            - (2 * risk)
        )

        side = "SELL"

    return TradePlan(
        strategy=signal.strategy,
        side=side,
        signal_timestamp=signal.timestamp,
        entry=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
    )



def register_trade(
    account: AccountState,
) -> AccountState:
    """Register one planned trade against that account's daily limits."""

    if not can_open_trade(account):
        raise TradingRuleError(
            f"Daily trading limit reached for {account.name}"
        )

    return AccountState(
        name=account.name,
        starting_balance=account.starting_balance,
        planned_risk_used=(
            account.planned_risk_used
            + RISK_PER_TRADE_INR
        ),
        trades_today=(
            account.trades_today
            + 1
        ),
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
        raise TradingRuleError(
            "Trade is already closed"
        )

    exit_timestamp = pd.Timestamp(
        exit_timestamp
    )

    if exit_timestamp.tzinfo is None:
        raise TradingRuleError(
            "Exit timestamp must be timezone-aware"
        )

    exit_price = float(exit_price)

    if exit_price <= 0:
        raise TradingRuleError(
            "Exit price must be positive"
        )

    if not exit_reason.strip():
        raise TradingRuleError(
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
