"""Canonical live TrendPulse market-data pipeline."""
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from config import NSE_15_SYMBOLS, IST_TIMEZONE
from market_data import MarketDataError, build_nse_hourly_candles, yahoo_symbol
from signal_gate import SignalGate
from strategies import StrategySignal, trendpulse_from_frames, derive_4h_from_1h
from yahoo_provider import YahooDataError, YahooProvider

@dataclass(frozen=True)
class TrendPulseScanResult:
    symbol: str
    signal: StrategySignal
    fresh: bool
    accepted: bool
    reason: str

class TrendPulseRuntime:
    def __init__(self, *, provider: YahooProvider | None=None, gate: SignalGate | None=None) -> None:
        self.provider=provider or YahooProvider(); self.gate=gate or SignalGate()
    @staticmethod
    def _build_4h(frame_1h: pd.DataFrame) -> pd.DataFrame:
        return derive_4h_from_1h(frame_1h)
    def fetch_symbol_1h(self, symbol: str, *, period: str="30d") -> pd.DataFrame:
        yf_symbol=yahoo_symbol(symbol)
        minute=self.provider.fetch(yf_symbol, period=period, interval="1m", validate_hourly=False)
        return build_nse_hourly_candles(minute)
    @staticmethod
    def _current(now: pd.Timestamp|None) -> pd.Timestamp:
        current=pd.Timestamp.now(tz=IST_TIMEZONE) if now is None else pd.Timestamp(now)
        if current.tzinfo is None: raise ValueError("Runtime timestamp must be timezone-aware")
        return current.tz_convert(IST_TIMEZONE)
    def scan_symbol(self, symbol: str, *, now: pd.Timestamp|None=None, period: str="30d", accept_signal: bool=False) -> TrendPulseScanResult:
        normalized=symbol.strip().upper()
        if normalized not in NSE_15_SYMBOLS: raise MarketDataError(f"Symbol is outside fixed NSE-15 universe: {normalized}")
        one=self.fetch_symbol_1h(normalized, period=period); four=self._build_4h(one)
        signal=trendpulse_from_frames(one,four,completed_only=True); current=self._current(now)
        if signal.signal not in ("BUY","SELL"): return TrendPulseScanResult(normalized,signal,False,False,signal.reason)
        fresh=self.gate.is_fresh(signal,now=current)
        if not fresh: return TrendPulseScanResult(normalized,signal,False,False,"STALE_SIGNAL")
        if not accept_signal: return TrendPulseScanResult(normalized,signal,True,False,"READY_FOR_ACCEPTANCE")
        accepted=self.gate.accept(signal,symbol=normalized,now=current)
        return TrendPulseScanResult(normalized,signal,True,accepted,"ACCEPTED" if accepted else "DUPLICATE_SIGNAL_LIMIT")
    def scan_universe(self, *, now: pd.Timestamp|None=None, period: str="30d") -> list[TrendPulseScanResult]:
        results=[]
        for symbol in NSE_15_SYMBOLS:
            try: results.append(self.scan_symbol(symbol,now=now,period=period,accept_signal=False))
            except (YahooDataError,MarketDataError,ValueError) as exc:
                current=self._current(now); results.append(TrendPulseScanResult(symbol,StrategySignal("TrendPulse","NO_SIGNAL",current,"MARKET_DATA_ERROR"),False,False,str(exc)))
        return results
__all__=["TrendPulseRuntime","TrendPulseScanResult"]
