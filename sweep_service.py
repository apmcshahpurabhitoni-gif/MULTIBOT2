"""Canonical 19-asset Sweep V2 dispatch."""
from __future__ import annotations
from dataclasses import dataclass
from threading import RLock
import pandas as pd
from config import ACCOUNT_NAMES, ACCOUNT_SIZE_INR, IST_TIMEZONE, LIVE_ASSETS, LIVE_ASSET_MAP, RISK_PER_TRADE_INR
from db import DatabaseManager
from signal_gate import SignalGate
from strategies import StrategySignal
from sweep_engine import detect_sweep
from telegram import TelegramConfig, TelegramMessage, render_signal_message, send_message, signal_rejection_message
from trading import AccountState, PaperTrade, can_open_trade, make_sweep_trade_plan, quantity_for_risk, register_trade
from trendpulse_runtime import TrendPulseRuntime

@dataclass(frozen=True)
class SweepDispatchResult:
    symbol:str; signal:StrategySignal; trade:PaperTrade|None; message:TelegramMessage|None
    sent:bool; reason:str; account:str="sweep_4h"

class SweepService:
    DEFAULT_ACCOUNT="sweep_4h"
    def __init__(self,*,runtime=None,telegram_config=None,database=None,accounts=None):
        self.runtime=runtime or TrendPulseRuntime(); self.telegram_config=telegram_config
        self.database=database or DatabaseManager(); self.gate=SignalGate(); self._lock=RLock()
        if accounts is not None: self.accounts=accounts
        else:
            rows=self.database.load_accounts(ACCOUNT_NAMES,ACCOUNT_SIZE_INR,pd.Timestamp.now(tz=IST_TIMEZONE).date().isoformat())
            self.accounts={n:AccountState(n,float(rows[n]["starting_balance"]),float(rows[n]["balance"]),float(rows[n]["planned_risk_used"]),int(rows[n]["trades_today"])) for n in ACCOUNT_NAMES}
    def _now(self,v):
        t=pd.Timestamp.now(tz=IST_TIMEZONE) if v is None else pd.Timestamp(v)
        if t.tzinfo is None: raise ValueError("Runtime timestamp must be timezone-aware")
        return t.tz_convert(IST_TIMEZONE)
    def _config(self): return self.telegram_config or TelegramConfig.from_env()
    def _fetch(self,asset,period): return self.runtime.fetch_sweep_frame(asset.symbol,period=period)
    def _price(self,asset):
        try:
            frame=self.runtime.provider.fetch(asset.yahoo_symbol,period="2d",interval="1m",validate_hourly=False)
            return None if frame.empty else float(frame.close.iloc[-1])
        except Exception: return None

    def dispatch(self,asset,signal,candles_1h,*,current_price,now=None,send=True,account_name=DEFAULT_ACCOUNT):
        asset=LIVE_ASSET_MAP[asset] if isinstance(asset,str) else asset; current=self._now(now)
        if signal.signal not in ("BUY","SELL"): return SweepDispatchResult(asset.symbol,signal,None,None,False,"NO_DIRECTIONAL_SIGNAL",account_name)
        if not self.gate.is_fresh(signal,now=current): return SweepDispatchResult(asset.symbol,signal,None,None,False,"STALE_SIGNAL",account_name)
        key=self.gate.signal_key(signal,symbol=asset.symbol)
        with self._lock:
            count=self.database.signal_count(key)
            if count>=2: return SweepDispatchResult(asset.symbol,signal,None,None,False,"DUPLICATE_SIGNAL_LIMIT",account_name)
            if count==1: return SweepDispatchResult(asset.symbol,signal,None,None,False,"REMINDER_PENDING",account_name)
            account=self.accounts[account_name]
            if not can_open_trade(account): return SweepDispatchResult(asset.symbol,signal,None,None,False,"ACCOUNT_DAILY_LIMIT",account_name)
            sweep=detect_sweep(candles_1h,asset.symbol,current)
            if sweep is None: return SweepDispatchResult(asset.symbol,signal,None,None,False,"NO_VALID_SWEEP",account_name)
            plan=make_sweep_trade_plan(signal,entry=float(current_price),signal_high=float(sweep.current["high"]),signal_low=float(sweep.current["low"]))
            if plan is None: return SweepDispatchResult(asset.symbol,signal,None,None,False,"NO_DIRECTIONAL_SIGNAL",account_name)
            qty=quantity_for_risk(plan.entry,plan.stop_loss); trade=PaperTrade(plan=plan,account=account_name,quantity=qty)
            age=max(0,int((current-signal.timestamp).total_seconds()/60)); age_text=f"{age} min ago" if age<60 else f"{age//60} hr {age%60} min ago"
            message=render_signal_message(signal,symbol=asset.symbol,asset=asset.label,market=asset.market,timeframe=asset.sweep_timeframe,
                entry=plan.entry,stop_loss=plan.stop_loss,take_profit=plan.take_profit,quantity=qty,risk=trade.planned_risk,
                account=account_name,freshness="FRESH",age_str=age_text)
            if not send: return SweepDispatchResult(asset.symbol,signal,trade,message,False,"READY_TO_SEND",account_name)
            updated=register_trade(account,planned_risk=trade.planned_risk); self.accounts[account_name]=updated
            trade_id=f"{account_name}_{asset.symbol}_{int(current.timestamp()*1000)}"
            trade_row={"id":trade_id,"status":"OPEN","symbol":asset.symbol,"market":asset.market,"account":account_name,
                       "strategy":"Sweep V2","type":signal.signal,"entry":trade.plan.entry,"sl":trade.plan.stop_loss,
                       "tp":trade.plan.take_profit,"qty":trade.quantity,"risk_per_unit":trade.plan.risk_per_unit,
                       "planned_risk":trade.planned_risk,"signal_ts":signal.timestamp.isoformat(),"opened_at":current.isoformat()}
            self.database.save_trade(trade_id,"OPEN",trade_row,current.isoformat())
            self.database.save_account(account_name,balance=updated.balance,trades_today=updated.trades_today,planned_risk_used=updated.planned_risk_used,reset_date=current.date().isoformat())
            send_message(message,self._config())
            metadata={"message_type":message.message_type,"strategy":"Sweep V2","symbol":asset.symbol,"asset":asset.label,"label":asset.label,
                      "market":asset.market,"asset_type":asset.asset_type,"group":asset.group,"timeframe":asset.sweep_timeframe,
                      "direction":signal.signal,"timestamp":signal.timestamp.isoformat(),"reason":signal.reason}
            self.database.record_signal_send(key,current.isoformat(),(current+pd.Timedelta(hours=1)).isoformat(),message.text,metadata)
            self.gate.accept(signal,symbol=asset.symbol,now=current)
            return SweepDispatchResult(asset.symbol,signal,trade,message,True,"SENT_AND_ACCEPTED",account_name,trade_id)

    def scan_symbol(self,symbol,*,period="30d",now=None):
        asset=LIVE_ASSET_MAP[symbol.strip().upper()]; current=self._now(now); frame=self._fetch(asset,period)
        result=detect_sweep(frame,asset.symbol,current)
        if result is None:
            return StrategySignal("Sweep V2","NO_SIGNAL",current,"NO_SWEEP"),frame
        direction={"BULLISH":"BUY","BEARISH":"SELL","NEUTRAL":"NEUTRAL"}.get(result.direction,"NO_SIGNAL")
        return StrategySignal("Sweep V2",direction,result.candle_end,result.direction),frame

    def scan_universe_and_dispatch(self,*,now=None,period="30d",send=True):
        current=self._now(now); output=[]
        for asset in LIVE_ASSETS:
            try:
                signal,frame=self.scan_symbol(asset.symbol,period=period,now=current)
                if signal.signal not in ("BUY","SELL"):
                    output.append(SweepDispatchResult(asset.symbol,signal,None,None,False,"NO_DIRECTIONAL_SIGNAL",self.DEFAULT_ACCOUNT)); continue
                price=self._price(asset)
                if price is None:
                    output.append(SweepDispatchResult(asset.symbol,signal,None,None,False,"MARKET_DATA_ERROR",self.DEFAULT_ACCOUNT)); continue
                output.append(self.dispatch(asset,signal,frame,current_price=price,now=current,send=send))
            except Exception as exc:
                output.append(SweepDispatchResult(asset.symbol,StrategySignal("Sweep V2","NO_SIGNAL",current,"MARKET_DATA_ERROR"),None,None,False,f"MARKET_DATA_ERROR: {exc}",self.DEFAULT_ACCOUNT))
        return output
    def start(self,*_,**__): return None
    def stop(self): return None
