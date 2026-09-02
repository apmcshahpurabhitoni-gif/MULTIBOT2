"""Backtesting boundary for MULTIBOT2.

Live and backtest paths call the same strategy functions. Account limits are
independent: macro=20, nifty=5, ny_session=3, sweep_4h=3.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
import pandas as pd
from config import ACCOUNT_SIZE_INR, ACCOUNT_TRADE_LIMITS, RISK_PER_TRADE_INR
from strategies import StrategySignal, derive_4h_from_1h, sweep_v2, trendpulse_from_frames
from sweep_engine import build_closed_candles
@dataclass(frozen=True)
class BacktestSignal:
    signal: StrategySignal
    candle_timestamp: pd.Timestamp
@dataclass(frozen=True)
class BacktestResult:
    strategy: str
    starting_account: float
    signals: tuple[BacktestSignal,...]
    trades_taken: int
    planned_risk: float
    account: str="nifty"
    @property
    def total_signals(self)->int: return len(self.signals)
    @property
    def buy_signals(self)->int: return sum(x.signal.signal=="BUY" for x in self.signals)
    @property
    def sell_signals(self)->int: return sum(x.signal.signal=="SELL" for x in self.signals)
    @property
    def neutral_signals(self)->int: return sum(x.signal.signal in {"NEUTRAL","NO_SIGNAL"} for x in self.signals)
def _validate_input(candles:pd.DataFrame)->None:
    if not isinstance(candles,pd.DataFrame): raise TypeError("candles must be a pandas DataFrame")
    if not isinstance(candles.index,pd.DatetimeIndex): raise ValueError("candles must use a DatetimeIndex")
    if candles.index.tz is None: raise ValueError("Backtest timestamps must be timezone-aware")
def _limit(account:str)->int:
    if account not in ACCOUNT_TRADE_LIMITS: raise ValueError(f"Unknown account: {account}")
    return int(ACCOUNT_TRADE_LIMITS[account])
def _apply_limit(signals:list[BacktestSignal],account:str)->tuple[int,float]:
    limit=_limit(account); counts={}; taken=0
    for item in signals:
        if item.signal.signal not in {"BUY","SELL"}: continue
        day=item.candle_timestamp.tz_convert("Asia/Kolkata").date().isoformat()
        if counts.get(day,0)>=limit: continue
        counts[day]=counts.get(day,0)+1; taken+=1
    return taken,taken*RISK_PER_TRADE_INR
def run_signal_backtest(candles:pd.DataFrame,evaluator:Callable[[pd.Series,pd.Series],StrategySignal],*,strategy_name:str,account:str="nifty")->BacktestResult:
    _validate_input(candles); frame=candles.sort_index()
    if frame.index.has_duplicates: raise ValueError("Backtest candles contain duplicate timestamps")
    results=[]
    for i in range(1,len(frame)):
        current=frame.iloc[i]; signal=evaluator(frame.iloc[i-1],current)
        if not isinstance(signal,StrategySignal): raise TypeError("Strategy evaluator must return StrategySignal")
        results.append(BacktestSignal(signal,current.name))
    taken,risk=_apply_limit(results,account)
    return BacktestResult(strategy_name,ACCOUNT_SIZE_INR,tuple(results),taken,risk,account)
def sweep_backtest(candles: pd.DataFrame, *, symbol: str | None = None, account: str = "sweep_4h") -> BacktestResult:
    _validate_input(candles)
    frame = candles.sort_index()
    if frame.index.has_duplicates:
        raise ValueError("Backtest candles contain duplicate timestamps")

    if symbol:
        canonical = build_closed_candles(
            frame,
            symbol.strip().upper(),
            now=frame.index[-1] + pd.Timedelta(days=2),
            lookback_days=max(3, (frame.index[-1].date() - frame.index[0].date()).days + 2),
        )[0]
        frame = canonical

    results = []
    for i in range(1, len(frame)):
        current = frame.iloc[i]
        signal = sweep_v2(
            frame.iloc[i - 1],
            current,
            timestamp=current.name,
        )
        results.append(BacktestSignal(signal, current.name))

    taken, risk = _apply_limit(results, account)
    return BacktestResult("Sweep V2", ACCOUNT_SIZE_INR, tuple(results), taken, risk, account)
def trendpulse_backtest(candles_1h:pd.DataFrame,*,account:str="nifty")->BacktestResult:
    _validate_input(candles_1h); frame=candles_1h.sort_index()
    if frame.index.has_duplicates: raise ValueError("Backtest candles contain duplicate timestamps")
    results=[]
    for i in range(49,len(frame)):
        prefix=frame.iloc[:i+1]; four_h=derive_4h_from_1h(prefix)
        signal=trendpulse_from_frames(prefix,four_h,completed_only=True)
        results.append(BacktestSignal(signal,signal.timestamp))
    taken,risk=_apply_limit(results,account)
    return BacktestResult("TrendPulse",ACCOUNT_SIZE_INR,tuple(results),taken,risk,account)
