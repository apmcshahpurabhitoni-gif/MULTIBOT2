"""Backtesting engine for MULTIBOT2.

The backtester uses the same strategy functions as the live system.
It must never contain a second implementation of strategy rules.

Risk:
    ₹2,000 per trade

Account:
    ₹100,000

Maximum trades:
    3 per day

Leverage:
    1x

Unapproved fees/slippage are not invented.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from config import (
    ACCOUNT_SIZE_INR,
    MAX_TRADES_PER_DAY,
    RISK_PER_TRADE_INR,
)
from strategies import StrategySignal


@dataclass(frozen=True)
class BacktestSignal:
    """One signal generated during a backtest."""

    signal: StrategySignal
    candle_timestamp: pd.Timestamp


@dataclass(frozen=True)
class BacktestResult:
    """Signal-level backtest result."""

    strategy: str

    starting_account: float

    signals: tuple[BacktestSignal, ...]

    trades_taken: int

    planned_risk: float

    @property
    def total_signals(self) -> int:
        return len(self.signals)

    @property
    def buy_signals(self) -> int:
        return sum(
            item.signal.signal == "BUY"
            for item in self.signals
        )

    @property
    def sell_signals(self) -> int:
        return sum(
            item.signal.signal == "SELL"
            for item in self.signals
        )

    @property
    def neutral_signals(self) -> int:
        return sum(
            item.signal.signal == "NEUTRAL"
            for item in self.signals
        )


def _validate_input(
    candles: pd.DataFrame,
) -> None:
    if not isinstance(
        candles,
        pd.DataFrame,
    ):
        raise TypeError(
            "candles must be a pandas DataFrame"
        )

    if not isinstance(
        candles.index,
        pd.DatetimeIndex,
    ):
        raise ValueError(
            "candles must use a DatetimeIndex"
        )

    if candles.index.tz is None:
        raise ValueError(
            "Backtest timestamps must be timezone-aware"
        )


def run_signal_backtest(
    candles: pd.DataFrame,
    evaluator: Callable[
        [pd.Series, pd.Series],
        StrategySignal,
    ],
    *,
    strategy_name: str,
) -> BacktestResult:
    """Run a deterministic signal backtest.

    Only completed candles are evaluated.

    The same evaluator used by the live strategy layer must
    be supplied here.

    The daily three-trade limit is enforced.
    """

    _validate_input(candles)

    candles = candles.sort_index()

    if candles.index.has_duplicates:
        raise ValueError(
            "Backtest candles contain duplicate timestamps"
        )

    results: list[BacktestSignal] = []

    trades_taken = 0

    planned_risk = 0.0

    daily_trade_count: dict[str, int] = {}

    for position in range(
        1,
        len(candles),
    ):

        previous = candles.iloc[
            position - 1
        ]

        current = candles.iloc[
            position
        ]

        timestamp = candles.index[
            position
        ]

        signal = evaluator(
            previous,
            current,
        )

        if not isinstance(
            signal,
            StrategySignal,
        ):
            raise TypeError(
                "Strategy evaluator must return StrategySignal"
            )

        results.append(
            BacktestSignal(
                signal=signal,
                candle_timestamp=timestamp,
            )
        )

        if signal.signal not in {
            "BUY",
            "SELL",
        }:
            continue

        trading_day = (
            timestamp
            .tz_convert("Asia/Kolkata")
            .date()
            .isoformat()
        )

        count = daily_trade_count.get(
            trading_day,
            0,
        )

        if count >= MAX_TRADES_PER_DAY:
            continue

        daily_trade_count[
            trading_day
        ] = count + 1

        trades_taken += 1

        planned_risk += RISK_PER_TRADE_INR

    return BacktestResult(
        strategy=strategy_name,
        starting_account=ACCOUNT_SIZE_INR,
        signals=tuple(results),
        trades_taken=trades_taken,
        planned_risk=planned_risk,
    )


def sweep_backtest(
    candles: pd.DataFrame,
) -> BacktestResult:
    """Backtest Sweep V2 using the canonical strategy."""

    from strategies import sweep_v2

    def evaluate(
        previous: pd.Series,
        current: pd.Series,
    ) -> StrategySignal:

        return sweep_v2(
            previous,
            current,
            timestamp=current.name,
        )

    return run_signal_backtest(
        candles,
        evaluate,
        strategy_name="Sweep V2",
    )


def trendpulse_backtest(
    candles: pd.DataFrame,
) -> BacktestResult:
    """TrendPulse backtest boundary.

    TrendPulse remains fail-closed until its exact approved
    specification is recovered and implemented.
    """

    signals: list[BacktestSignal] = []

    for timestamp in candles.index:

        signal = StrategySignal(
            strategy="TrendPulse",
            signal="NO_SIGNAL",
            timestamp=timestamp,
            reason=(
                "TREND_PULSE_RULES_NOT_YET_VERIFIED"
            ),
        )

        signals.append(
            BacktestSignal(
                signal=signal,
                candle_timestamp=timestamp,
            )
        )

    return BacktestResult(
        strategy="TrendPulse",
        starting_account=ACCOUNT_SIZE_INR,
        signals=tuple(signals),
        trades_taken=0,
        planned_risk=0.0,
    )
