"""Backtest boundary for MULTIBOT2.

Backtests consume the same canonical strategy functions used by the live
pipeline. This first foundation deliberately performs no broker simulation,
position sizing, fees, or slippage because those rules are not yet frozen.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

import pandas as pd

from strategies import StrategySignal


@dataclass(frozen=True)
class BacktestResult:
    signals: tuple[StrategySignal, ...]


def run_backtest(
    rows: Iterable[tuple[pd.Series, pd.Series, pd.Timestamp]],
    strategy: Callable[[pd.Series, pd.Series], StrategySignal],
) -> BacktestResult:
    """Run a supplied canonical strategy over prepared historical rows.

    The caller supplies the canonical strategy adapter. No second copy of
    strategy rules is allowed in this module.
    """
    results: list[StrategySignal] = []
    for previous, current, timestamp in rows:
        result = strategy(previous, current, timestamp)
        results.append(result)
    return BacktestResult(tuple(results))
