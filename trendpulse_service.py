"""Canonical TrendPulse dispatch. Strategy generation remains in strategies.py."""
from __future__ import annotations
from dataclasses import dataclass
from threading import RLock
import pandas as pd
from config import ACCOUNT_NAMES, ACCOUNT_SIZE_INR, IST_TIMEZONE, LIVE_ASSET_MAP, RISK_PER_TRADE_INR, SIGNAL_FRESHNESS_HOURS
from db import DatabaseManager
from strategies import calc_sl_tp
from telegram import TelegramConfig, TelegramMessage, render_signal_message, send_message, signal_rejection_message
from trading import AccountState, PaperTrade, TradePlan, can_open_trade, register_trade
from trendpulse_runtime import TrendPulseRuntime, TrendPulseScanResult

@dataclass(frozen=True)
class TrendPulseDispatchResult:
    symbol:str; signal:object; scan:TrendPulseScanResult; trade:PaperTrade|None
    message:TelegramMessage|None; sent:bool; reason:str; account:str="nifty"; trade_id:str|None=None

class TrendPulseService:
    DEFAULT_ACCOUNT="nifty"
    def __init__(self,*,runtime=None,telegram_config=None,database=None,accounts=None):
        self.runtime=runtime or TrendPulseRuntime()
        self.telegram_config=telegram_config
        self.database=database or DatabaseManager()
        self._lock=RLock()
        if accounts is not None: self.accounts=accounts
        else:
            rows=self.database.load_accounts(ACCOUNT_NAMES,ACCOUNT_SIZE_INR,pd.Timestamp.now(tz=IST_TIMEZONE).date().isoformat())
            self.accounts={n:AccountState(n,float(rows[n]["starting_balance"]),float(rows[n]["balance"]),float(rows[n]["planned_risk_used"]),int(rows[n]["trades_today"])) for n in ACCOUNT_NAMES}

    def _now(self,value):
        t=pd.Timestamp.now(tz=IST_TIMEZONE) if value is None else pd.Timestamp(value)
        if t.tzinfo is None: raise ValueError("Runtime timestamp must be timezone-aware")
        return t.tz_convert(IST_TIMEZONE)
    def _config(self): return self.telegram_config or TelegramConfig.from_env()
    def _reject(self,symbol,signal,reason,account):
        return TrendPulseDispatchResult(symbol,signal,None,None,signal_rejection_message(strategy=getattr(signal,"strategy","TrendPulse"),symbol=symbol,reason=reason),False,reason,account)

    def dispatch_result(self,scan,*,now=None,send=True,account_name=DEFAULT_ACCOUNT):
        signal=scan.signal; current=self._now(now); asset=LIVE_ASSET_MAP[scan.symbol]; account=self.accounts[account_name]
        if signal.signal not in ("BUY","SELL"): return TrendPulseDispatchResult(scan.symbol,signal,scan,None,None,False,"NO_DIRECTIONAL_SIGNAL",account_name)
        if not scan.fresh or self.runtime.gate.age_hours(signal,now=current)>SIGNAL_FRESHNESS_HOURS: return self._reject(scan.symbol,signal,"STALE_SIGNAL",account_name)
        key=self.runtime.gate.signal_key(signal,symbol=scan.symbol)
        with self._lock:
            count=self.database.signal_count(key)
            if count>=2: return self._reject(scan.symbol,signal,"DUPLICATE_SIGNAL_LIMIT",account_name)
            if count==1: return self._reject(scan.symbol,signal,"REMINDER_PENDING",account_name)
            if not can_open_trade(account): return self._reject(scan.symbol,signal,"ACCOUNT_DAILY_LIMIT",account_name)
            sl,tp=calc_sl_tp(signal); entry=float(signal.entry)
            plan=TradePlan(signal.strategy,signal.signal,signal.timestamp,entry,sl,tp)
            qty=RISK_PER_TRADE_INR/plan.risk_per_unit
            trade=PaperTrade(plan=plan,account=account_name,quantity=qty)
            age_m=max(0,int(self.runtime.gate.age_hours(signal,now=current)*60))
            age=f"{age_m} min ago" if age_m<60 else f"{age_m//60} hr {age_m%60} min ago"
            message=render_signal_message(signal,symbol=asset.symbol,asset=asset.label,market=asset.market,
                timeframe=asset.trendpulse_signal_timeframe,entry=entry,stop_loss=sl,take_profit=tp,quantity=qty,
                risk=trade.planned_risk,account=account_name,freshness="FRESH",age_str=age)
            if not send: return TrendPulseDispatchResult(scan.symbol,signal,scan,trade,message,False,"READY_TO_SEND",account_name)
            # Canonical order: persist the paper trade/account and signal intent
            # before any external Telegram side effect. The main runtime may
            # safely persist the same trade again (SQLite/Supabase upsert).
            updated=register_trade(account,planned_risk=trade.planned_risk); self.accounts[account_name]=updated
            trade_id=f"{account_name}_{asset.symbol}_{int(current.timestamp()*1000)}"
            trade_row={"id":trade_id,"status":"OPEN","symbol":asset.symbol,"market":asset.market,"account":account_name,
                       "strategy":signal.strategy,"type":signal.signal,"entry":trade.plan.entry,"sl":trade.plan.stop_loss,
                       "tp":trade.plan.take_profit,"qty":trade.quantity,"risk_per_unit":trade.plan.risk_per_unit,
                       "planned_risk":trade.planned_risk,"signal_ts":signal.timestamp.isoformat(),"opened_at":current.isoformat()}
            self.database.save_trade(trade_id,"OPEN",trade_row,current.isoformat())
            self.database.save_account(account_name,balance=updated.balance,trades_today=updated.trades_today,planned_risk_used=updated.planned_risk_used,reset_date=current.date().isoformat())
            metadata={"message_type":message.message_type,"strategy":signal.strategy,"symbol":asset.symbol,"asset":asset.label,
                      "label":asset.label,"market":asset.market,"asset_type":asset.asset_type,"group":asset.group,
                      "timeframe":asset.trendpulse_signal_timeframe,"filter_timeframe":asset.trendpulse_filter_timeframe,
                      "direction":signal.signal,"timestamp":signal.timestamp.isoformat(),"reason":signal.reason}
            send_message(message,self._config())
            self.database.record_signal_send(key,current.isoformat(),(current+pd.Timedelta(hours=1)).isoformat(),message.text,metadata)
            self.runtime.gate.accept(signal,symbol=asset.symbol,now=current)
            return TrendPulseDispatchResult(scan.symbol,signal,scan,trade,message,True,"SENT_AND_ACCEPTED",account_name,trade_id)

    def scan_and_dispatch(self,symbol,*,now=None,period="30d",send=True,account_name=DEFAULT_ACCOUNT):
        return self.dispatch_result(self.runtime.scan_symbol(symbol,now=now,period=period),now=now,send=send,account_name=account_name)
    def scan_universe_and_dispatch(self,*,now=None,period="30d",send=True,account_name=DEFAULT_ACCOUNT):
        return [self.dispatch_result(s,now=now,send=send,account_name=account_name) for s in self.runtime.scan_universe(now=now,period=period)]
