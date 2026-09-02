"""Canonical Sweep V2 dispatch service.

Directional Sweep signals use exactly the same acceptance boundary as every
other strategy. There is no second direct-send path and no pending-sweep state.
"""
from __future__ import annotations
from dataclasses import dataclass
from threading import RLock
import pandas as pd
from config import ACCOUNT_NAMES,ACCOUNT_SIZE_INR,IST_TIMEZONE,NSE_15_SYMBOLS,RISK_PER_TRADE_INR
from db import DatabaseManager
from signal_gate import SignalGate
from strategies import StrategySignal
from sweep_engine import detect_sweep
from telegram import TelegramConfig,TelegramMessage,render_signal_message,send_message,signal_rejection_message
from trading import AccountState,PaperTrade,can_open_trade,make_sweep_trade_plan,quantity_for_risk,register_trade
from trendpulse_runtime import TrendPulseRuntime
CRYPTO_SYMBOLS=("BTC-USD",); FOREX_GOLD_SYMBOLS=("GC=F","EURUSD=X","GBPUSD=X","USDJPY=X","USDCHF=X","AUDUSD=X","USDCAD=X","NZDUSD=X"); NIFTY_SYMBOLS=("^NSEI","^NSEBANK")
@dataclass(frozen=True)
class SweepDispatchResult:
    symbol:str; signal:StrategySignal; trade:PaperTrade|None; message:TelegramMessage|None; sent:bool; reason:str; account:str="sweep_4h"
class SweepService:
    DEFAULT_ACCOUNT="sweep_4h"
    def __init__(self,*,runtime=None,telegram_config=None,database=None,accounts=None):
        self.runtime=runtime or TrendPulseRuntime(); self.telegram_config=telegram_config; self.database=database or DatabaseManager(); self.gate=SignalGate(); self._lock=RLock()
        if accounts is not None:self.accounts=accounts
        else:
            rows=self.database.load_accounts(ACCOUNT_NAMES,ACCOUNT_SIZE_INR,pd.Timestamp.now(tz=IST_TIMEZONE).date().isoformat()); self.accounts={n:AccountState(n,float(rows[n]["starting_balance"]),float(rows[n]["balance"]),float(rows[n]["planned_risk_used"]),int(rows[n]["trades_today"])) for n in ACCOUNT_NAMES}
    def _config(self):return self.telegram_config or TelegramConfig.from_env()
    def _now(self,now):
        t=pd.Timestamp.now(tz=IST_TIMEZONE) if now is None else pd.Timestamp(now)
        if t.tzinfo is None:raise ValueError("Runtime timestamp must be timezone-aware")
        return t.tz_convert(IST_TIMEZONE)
    def _reject(self,symbol,signal,reason,*,account_name=DEFAULT_ACCOUNT,detail=""):
        return SweepDispatchResult(symbol,signal,None,signal_rejection_message(strategy="Sweep",symbol=symbol,reason=reason,detail=detail),False,reason,account_name)
    def _fetch(self,symbol,period="30d"):
        return self.runtime.fetch_symbol_1h(symbol,period=period) if symbol.endswith(".NS") else self.runtime.provider.fetch(symbol,period=period,interval="1h",validate_hourly=False)
    def _price(self,symbol):
        try:
            frame=self.runtime.provider.fetch(symbol,period="2d",interval="1m",validate_hourly=False); return None if frame.empty else float(frame.close.iloc[-1])
        except Exception:return None
    def _build_dispatch(self,symbol,signal,candles_1h,*,current_price,now,account_name):
        if signal.signal not in ("BUY","SELL"):return self._reject(symbol,signal,"NO_DIRECTIONAL_SIGNAL",account_name=account_name)
        if not self.gate.is_fresh(signal,now=now):return self._reject(symbol,signal,"STALE_SIGNAL",account_name=account_name)
        key=self.gate.signal_key(signal,symbol=symbol)
        with self._lock:
            count=self.database.signal_count(key)
            if count>=2:return self._reject(symbol,signal,"DUPLICATE_SIGNAL_LIMIT",account_name=account_name)
            if count==1:return self._reject(symbol,signal,"REMINDER_PENDING",account_name=account_name)
            account=self.accounts[account_name]
            if not can_open_trade(account):return self._reject(symbol,signal,"ACCOUNT_DAILY_LIMIT",account_name=account_name)
            if candles_1h is None or candles_1h.empty:return self._reject(symbol,signal,"MISSING_SIGNAL_CANDLE",account_name=account_name)
            candle=candles_1h.iloc[-1]; plan=make_sweep_trade_plan(signal,entry=float(current_price),signal_high=float(candle.high),signal_low=float(candle.low))
            if plan is None:return self._reject(symbol,signal,"NO_DIRECTIONAL_SIGNAL",account_name=account_name)
            qty=quantity_for_risk(plan.entry,plan.stop_loss); trade=PaperTrade(plan=plan,account=account_name,quantity=qty); age=max(0,int((now-signal.timestamp).total_seconds()/60)); age_text=f"{age} min ago" if age<60 else f"{age//60} hr {age%60} min ago"; market="Crypto" if symbol=="BTC-USD" else "Forex / Gold" if symbol in FOREX_GOLD_SYMBOLS else "NSE"; asset={"BTC-USD":"Bitcoin (BTC)","GC=F":"Gold (XAU/USD)","^NSEI":"NIFTY 50","^NSEBANK":"BANK NIFTY"}.get(symbol,symbol.replace(".NS","")); msg=render_signal_message(signal,symbol=symbol,asset=asset,market=market,timeframe="4H",entry=plan.entry,stop_loss=plan.stop_loss,take_profit=plan.take_profit,quantity=qty,risk=trade.planned_risk,account=account_name,freshness="FRESH",age_str=age_text)
            if not self.telegram_config and not self.database.supabase_enabled: pass
            if not getattr(self,"_send_enabled",True): return SweepDispatchResult(symbol,signal,trade,msg,False,"READY_TO_SEND",account_name)
            send_message(msg,self._config())
            self.database.record_signal_send(key,now.isoformat(),(now+pd.Timedelta(hours=1)).isoformat(),msg.text,{"message_type":msg.message_type,"strategy":signal.strategy,"symbol":symbol,"direction":signal.signal,"timestamp":signal.timestamp.isoformat()})
            updated=register_trade(account,planned_risk=trade.planned_risk); self.accounts[account_name]=updated; self.database.save_account(account_name,balance=updated.balance,trades_today=updated.trades_today,planned_risk_used=updated.planned_risk_used,reset_date=now.date().isoformat()); self.gate.accept(signal,symbol=symbol,now=now)
            return SweepDispatchResult(symbol,signal,trade,msg,True,"SENT_AND_ACCEPTED",account_name)
    def dispatch(self,symbol,signal,candles_1h,*,current_price,now=None,send=True,account_name=DEFAULT_ACCOUNT):
        current=self._now(now); old=getattr(self,"_send_enabled",True); self._send_enabled=send
        try:return self._build_dispatch(symbol,signal,candles_1h,current_price=current_price,now=current,account_name=account_name)
        finally:self._send_enabled=old
    def scan_symbol(self,symbol,*,period="30d"):
        symbol=symbol.strip().upper(); frame=self._fetch(symbol,period); result=detect_sweep(frame,symbol,pd.Timestamp.now(tz=IST_TIMEZONE)); ts=result.candle_end if result else (frame.index[-1] if len(frame) else pd.Timestamp.now(tz=IST_TIMEZONE)); direction={"BULLISH":"BUY","BEARISH":"SELL","NEUTRAL":"NEUTRAL"}.get(result.direction if result else "","NO_SIGNAL"); return StrategySignal("Sweep V2",direction,ts,result.direction if result else "NO_SIGNAL"),frame
    def scan_universe_and_dispatch(self,*,now=None,period="30d",send=True):
        current=self._now(now); out=[]
        for symbol in NSE_15_SYMBOLS:
            try:
                signal,frame=self.scan_symbol(symbol,period=period)
                if signal.signal not in ("BUY","SELL"):continue
                price=self._price(symbol+".NS")
                if price is not None:out.append(self.dispatch(symbol,signal,frame,current_price=price,now=current,send=send,account_name=self.DEFAULT_ACCOUNT))
            except Exception:continue
        return out
    def start(self,*_,**__):return None
    def stop(self):return None
__all__=["SweepDispatchResult","SweepService"]