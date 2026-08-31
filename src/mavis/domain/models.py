from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Signal(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"
    NO_SIGNAL = "NO_SIGNAL"


class Freshness(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"


class Instrument(BaseModel):
    model_config = ConfigDict(frozen=True)
    canonical_symbol: str
    display_symbol: str
    exchange: str


class MarketSession(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    timezone: str
    start: datetime
    end: datetime

    @field_validator("start", "end")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime must be timezone-aware")
        return value


class Candle(BaseModel):
    model_config = ConfigDict(frozen=True)
    instrument: str
    timeframe: str
    start: datetime
    end: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    closed: bool = False

    @field_validator("start", "end")
    @classmethod
    def candle_timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("candle datetime must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_ohlc(self) -> "Candle":
        if self.high < self.low:
            raise ValueError("high cannot be below low")
        if self.open < self.low or self.open > self.high:
            raise ValueError("open must be within candle range")
        if self.close < self.low or self.close > self.high:
            raise ValueError("close must be within candle range")
        if self.end <= self.start:
            raise ValueError("candle end must be after start")
        return self


class StrategyInput(BaseModel):
    model_config = ConfigDict(frozen=True)
    instrument: Instrument
    candles: tuple[Candle, ...] = Field(default_factory=tuple)
    config_version: str


class Warning(BaseModel):
    code: str
    message: str
    severity: str = "WARNING"


class SignalResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    strategy: str
    strategy_version: str
    instrument: str
    signal: Signal
    candle_start: datetime
    candle_close: datetime
    confirmation_time: datetime
    entry: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    reason: str
    freshness: Freshness
    data_source: str
    warnings: tuple[Warning, ...] = ()
    config_version: str


class TradePlan(BaseModel):
    model_config = ConfigDict(frozen=True)
    entry: Decimal
    stop_loss: Decimal
    take_profit: Decimal


class PaperTrade(BaseModel):
    model_config = ConfigDict(frozen=True)
    instrument: str
    signal: Signal
    plan: TradePlan


class MessageEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    message_id: str
    strategy: str
    instrument: str
    created_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class BacktestResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    strategy: str
    instrument: str
    trades: tuple[PaperTrade, ...] = ()
    signal_count: int = 0
