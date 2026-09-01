"""Backtesting boundary for MULTIBOT2.

Backtests use the same canonical strategy functions as live evaluation.
No separate strategy implementation is allowed here.

Risk/account rules are intentionally not invented.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from strategies import StrategySignal


@dataclass(frozen=True)
class BacktestSignal:
    """A strategy signal generated during a backtest."""

    signal: StrategySignal
    candle_timestamp: pd.Timestamp


@dataclass(frozen=True)
class BacktestResult:
    """Minimal deterministic backtest result."""

    strategy: str
    signals: tuple[BacktestSignal, ...]

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


def run_signal_backtest(
    candles: pd.DataFrame,
    evaluator: Callable[
        [pd.Series, pd.Series],
        StrategySignal,
    ],
    *,
    strategy_name: str,
) -> BacktestResult:
    """Run a signal-only backtest over completed candle pairs.

    ``evaluator`` must be the same strategy function used by live evaluation.
    This function does not invent entry, risk, fees, slippage or position
    sizing rules.
    """

    if not isinstance(candles, pd.DataFrame):
        raise TypeError(
            "candles must be a pandas DataFrame"
        )

    if not isinstance(candles.index, pd.DatetimeIndex):
        raise ValueError(
            "candles must use a DatetimeIndex"
        )

    if candles.index.tz is None:
        raise ValueError(
            "Backtest timestamps must be timezone-aware"
        )

    if len(candles) < 2:
        return BacktestResult(
            strategy=strategy_name,
            signals=(),
        )

    candles = candles.sort_index()

    results: list[BacktestSignal] = []

    for position in range(1, len(candles)):
        previous = candles.iloc[position - 1]
        current = candles.iloc[position]
        timestamp = candles.index[position]

        signal = evaluator(
            previous,
            current,
        )

        if not isinstance(signal, StrategySignal):
            raise TypeError(
                "Strategy evaluator must return StrategySignal"
            )

        results.append(
            BacktestSignal(
                signal=signal,
                candle_timestamp=timestamp,
            )
        )

    return BacktestResult(
        strategy=strategy_name,
        signals=tuple(results),
    )


def sweep_backtest(
    candles: pd.DataFrame,
) -> BacktestResult:
    """Backtest Sweep V2 using the canonical Sweep evaluator."""

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
