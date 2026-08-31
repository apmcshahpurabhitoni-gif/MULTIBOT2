from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from mavis.domain import SignalResult, StrategyInput


class Strategy(ABC):
    """Pure strategy boundary. Strategies return domain truth only."""

    name: str
    version: str

    @abstractmethod
    def evaluate(self, context: StrategyInput) -> SignalResult:
        raise NotImplementedError


class MarketDataProvider(ABC):
    """Provider boundary; concrete providers belong to the data phase."""

    name: str

    @abstractmethod
    def get_candles(self, instrument: Any, timeframe: str, start: Any, end: Any) -> Any:
        raise NotImplementedError
