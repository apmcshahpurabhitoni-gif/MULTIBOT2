"""Complete TrendPulse dispatch with persistent duplicate and reminder control."""
from __future__ import annotations
from dataclasses import dataclass
from threading import RLock
import pandas as pd
from config import ACCOUNT_NAMES,ACCOUNT_SIZE_INR,RISK_PER_TRADE_INR,IST_TIMEZONE,SIGNAL_FRESHNESS_HOURS
from db import DatabaseManager
from strategies import StrategySignal,calc_sl_tp
from telegram import TelegramConfig,TelegramMessage,render_signal_message,send_message
from trading import AccountState,PaperTrade,TradePlan,can_open_trade,register_trade
from trendpulse_runtime import TrendPulseRuntime,TrendPulseScanResult
@dataclass(frozen=True)
class TrendPulseDispatchResult:
    symbol:str;signal:StrategySignal;scan:TrendPulseScanResult;trade:PaperTrade|None;message:TelegramMessage|None;sent:bool;reason:str;account:str="nifty"
class TrendPulseService:
    DEFAULT_ACCOUNT="nifty"
    def __init__(self,*,runtime=None,telegram_config=None,database=None,accounts=None):
        self.runtime=runtime or TrendPulseRuntime();self.telegram_config=telegram_config;self.database=database or DatabaseManager();self._lock=RLock()
        if accounts is not None:self.accounts=accounts
        else:
            rows=self.database.load_accounts(ACCOUNT_NAMES,ACCOUNT_SIZE_INR,pd.Timestamp.now(tz=IST_TIMEZONE).date().isoformat());self.accounts={n:AccountState(n,float(rows[n]["starting_balance"]),float(rows[n]["balance"]),float(rows[n]["planned_risk_used"]),int(rows[n]["trades_today"])) for n in ACCOUNT_NAMES}
    def _now(self,now):
        t=pd.Timestamp.now(tz=IST_TIMEZONE) if now is None else pd.Timestamp(now)
        if t.tzinfo is None:raise ValueError("Runtime timestamp must be timezone-aware")
        return t.tz_convert(IST_TIMEZONE)
    def _config(self):return self.telegram_config or TelegramConfig.from_env()
    def dispatch_result(self,scan,*,now=None,send=True,account_name=DEFAULT_ACCOUNT):
        signal=scan.signal;current=self._now(now);account=self.accounts[account_name]
        if signal.signal not in ("BUY","SELL"):return TrendPulseDispatchResult(scan.symbol,signal,scan,None,None,False,"NO_DIRECTIONAL_SIGNAL",account_name)
        if not scan.fresh or self.runtime.gate.age_hours(signal,now=current)>SIGNAL_FRESHNESS_HOURS:return TrendPulseDispatchResult(scan.symbol,signal,scan,None,None,False,"STALE_SIGNAL",account_name)
        key=self.runtime.gate.signal_key(signal,symbol=scan.symbol);count=self.database.signal_count(key)
        with self._lock:
            if count>=2:return TrendPulseDispatchResult(scan.symbol,signal,scan,None,None,False,"DUPLICATE_SIGNAL_LIMIT",account_name)
            if count==1:return TrendPulseDispatchResult(scan.symbol,signal,scan,None,None,False,"REMINDER_PENDING",account_name)
            if not can_open_trade(account):return TrendPulseDispatchResult(scan.symbol,signal,scan,None,None,False,"ACCOUNT_DAILY_LIMIT",account_name)
            sl,tp=calc_sl_tp(signal);entry=float(signal.entry);plan=TradePlan(signal.strategy,signal.signal,signal.timestamp,entry,sl,tp);qty=RISK_PER_TRADE_INR/plan.risk_per_unit;trade=PaperTrade(plan=plan,account=account_name,quantity=qty);age_m=int(self.runtime.gate.age_hours(signal,now=current)*60);age=f"{age_m} min ago" if age_m<60 else f"{age_m//60} hr {age_m%60} min ago"
            message=render_signal_message(signal,symbol=f"{scan.symbol}.NS",asset=scan.symbol,market="NSE",timeframe="1H",entry=entry,stop_loss=sl,take_profit=tp,quantity=qty,risk=trade.planned_risk,account=account_name,freshness="FRESH",age_str=age)
            if not send:return TrendPulseDispatchResult(scan.symbol,signal,scan,trade,message,False,"READY_TO_SEND",account_name)
            send_message(message,self._config());self.database.record_signal_send(key,current.isoformat(),(current+pd.Timedelta(hours=1)).isoformat(),message.text,{"strategy":signal.strategy,"symbol":scan.symbol,"direction":signal.signal,"timestamp":signal.timestamp.isoformat()});updated=register_trade(account,planned_risk=trade.planned_risk);self.accounts[account_name]=updated;self.database.save_account(account_name,balance=updated.balance,trades_today=updated.trades_today,planned_risk_used=updated.planned_risk_used,reset_date=current.date().isoformat())
            self.runtime.gate.accept(signal,symbol=scan.symbol,now=current)
            return TrendPulseDispatchResult(scan.symbol,signal,scan,trade,message,True,"SENT_AND_ACCEPTED",account_name)
    def scan_and_dispatch(self,symbol,*,now=None,period="30d",send=True,account_name=DEFAULT_ACCOUNT):return self.dispatch_result(self.runtime.scan_symbol(symbol,now=now,period=period),now=now,send=send,account_name=account_name)
    def scan_universe_and_dispatch(self,*,now=None,period="30d",send=True,account_name=DEFAULT_ACCOUNT):return [self.dispatch_result(s,now=now,send=send,account_name=account_name) for s in self.runtime.scan_universe(now=now,period=period)]
__all__=["TrendPulseDispatchResult","TrendPulseService"]
