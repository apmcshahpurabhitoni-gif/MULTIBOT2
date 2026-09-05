from __future__ import annotations
import pandas as pd
from strategies.base import Signal, Strategy, StrategyManifest
from sweep_engine import detect_sweep
from config import LIVE_SYMBOLS, SWEEP_TIMEFRAME_BY_SYMBOL

class SweepV2Strategy(Strategy):
    manifest = StrategyManifest(
        id="sweep_v2", name="Sweep V2", version="2.0.0",
        description="Strict two-sided sweep followed by final-close classification.",
        assets=LIVE_SYMBOLS, timeframes=("1h","4h"), schedule="canonical_sweep_schedule",
        account="sweep_4h", capabilities=("signal","strategy_sl","risk_reward_tp","scheduled_scan","backtest"),
        parameters={"timeframe":{"type":"strategy","default":"asset_schedule"},"risk_reward":{"type":"number","default":2.0,"min":1.0,"max":10.0,"editable":False}},
    )
    def data_request(self, symbol, *, period="30d"):
        asset_market = "NSE" if symbol.startswith("^") or symbol in LIVE_SYMBOLS[:15] else "GLOBAL"
        return ("1h" if asset_market == "NSE" else "30m"), period

    def prepare_candles(self, symbol, candles, *, now):
        from sweep_engine import build_closed_candles
        closed, _, _ = build_closed_candles(candles, symbol, now=now, lookback_days=7)
        return closed

    def generate_signal(self, symbol, candles, *, now):
        result = detect_sweep(candles, symbol, now)
        timeframe = SWEEP_TIMEFRAME_BY_SYMBOL[symbol]
        if result is None:
            ts = candles.index[-1] if len(candles) else now
            return Signal(self.manifest.name,self.manifest.version,symbol,"NO_SIGNAL",ts,timeframe,"NO_SWEEP")
        direction={"BULLISH":"BUY","BEARISH":"SELL","NEUTRAL":"NEUTRAL"}.get(result.direction,"NO_SIGNAL")
        ts=result.candle_end
        entry=float(result.current["close"])
        if direction=="BUY": sl=float(result.current["low"]); tp=entry+2*(entry-sl)
        elif direction=="SELL": sl=float(result.current["high"]); tp=entry-2*(sl-entry)
        else: sl=tp=None
        return Signal(self.manifest.name,self.manifest.version,symbol,direction,ts,timeframe,result.direction,entry,sl,tp,{"candle_start":result.candle_start.isoformat(),"previous":result.previous,"current":result.current})

def create_strategy(): return SweepV2Strategy()
