"""Complete TrendPulse dispatch: scan -> freshness -> duplicate -> risk -> persistence -> Telegram."""
from __future__ import annotations
from dataclasses import dataclass
from threading import RLock
import pandas as pd
from config import ACCOUNT_NAMES, ACCOUNT_SIZE_INR, ACCOUNT_TRADE_LIMITS, RISK_PER_TRADE_INR, IST_TIMEZONE, SIGNAL_FRESHNESS_HOURS
from db import DatabaseManager
from strategies import StrategySignal, calc_sl_tp
from signal_gate import SignalGate
from telegram import TelegramConfig, TelegramMessage, render_signal_message, send_message
from trading import AccountState, PaperTrade, TradePlan, can_open_trade, register_trade
from trendpulse_runtime import TrendPulseRuntime, TrendPulseScanResult

@dataclass(frozen=True)
class TrendPulseDispatchResult:
    symbol:str; signal:StrategySignal; scan:TrendPulseScanResult; trade:PaperTrade|None; message:TelegramMessage|None; sent:bool; reason:str; account:str="nifty"

class TrendPulseService:
    DEFAULT_ACCOUNT="nifty"
    def __init__(self, *, runtime:TrendPulseRuntime|None=None, telegram_config:TelegramConfig|None=None, database:DatabaseManager|None=None, accounts:dict[str,AccountState]|None=None) -> None:
        self.runtime=runtime or TrendPulseRuntime(); self.telegram_config=telegram_config; self.database=database or DatabaseManager(); self._lock=RLock()
        if accounts is not None: self.accounts=accounts
        else:
            today=pd.Timestamp.now(tz=IST_TIMEZONE).date().isoformat(); rows=self.database.load_accounts(ACCOUNT_NAMES,ACCOUNT_SIZE_INR,today)
            self.accounts={n:AccountState(n,float(rows[n]["starting_balance"]),float(rows[n]["balance"]),float(rows[n]["planned_risk_used"]),int(rows[n]["trades_today"])) for n in ACCOUNT_NAMES}
    def _now(self, now:pd.Timestamp|None)->pd.Timestamp:
        current=pd.Timestamp.now(tz=IST_TIMEZONE) if now is None else pd.Timestamp(now)
        if current.tzinfo is None: raise ValueError("Runtime timestamp must be timezone-aware")
        return current.tz_convert(IST_TIMEZONE)
    def _config(self)->TelegramConfig:
        if self.telegram_config is None: self.telegram_config=TelegramConfig.from_env()
        return self.telegram_config
    def _account(self,name:str)->AccountState:
        if name not in self.accounts: raise ValueError(f"Unknown account: {name}")
        return self.accounts[name]
    def dispatch_result(self, scan:TrendPulseScanResult, *, now:pd.Timestamp|None=None, send:bool=True, account_name:str=DEFAULT_ACCOUNT)->TrendPulseDispatchResult:
        signal=scan.signal; current=self._now(now); account=self._account(account_name)
        if signal.signal not in ("BUY","SELL"): return TrendPulseDispatchResult(scan.symbol,signal,scan,None,None,False,"NO_DIRECTIONAL_SIGNAL",account_name)
        if not scan.fresh or self.runtime.gate.age_hours(signal,now=current)>SIGNAL_FRESHNESS_HOURS: return TrendPulseDispatchResult(scan.symbol,signal,scan,None,None,False,"STALE_SIGNAL",account_name)
        key=self.runtime.gate.signal_key(signal,symbol=scan.symbol)
        with self._lock:
            if self.database.signal_count(key)>=2 or not self.runtime.gate.can_send(signal,symbol=scan.symbol,now=current): return TrendPulseDispatchResult(scan.symbol,signal,scan,None,None,False,"DUPLICATE_SIGNAL_LIMIT",account_name)
            if not can_open_trade(account): return TrendPulseDispatchResult(scan.symbol,signal,scan,None,None,False,"ACCOUNT_DAILY_LIMIT",account_name)
            sl,tp=calc_sl_tp(signal); entry=float(signal.entry); plan=TradePlan(signal.strategy,signal.signal,signal.timestamp,entry,sl,tp); qty=RISK_PER_TRADE_INR/plan.risk_per_unit; trade=PaperTrade(plan=plan,account=account_name,quantity=qty)
            age_h=self.runtime.gate.age_hours(signal,now=current); mins=int(age_h*60); age=f"{mins} min ago" if mins<60 else f"{mins//60} hr {mins%60} min ago"
            message=render_signal_message(signal,symbol=f"{scan.symbol}.NS",asset=scan.symbol,market="NSE",timeframe="1H",entry=entry,stop_loss=sl,take_profit=tp,quantity=qty,risk=trade.planned_risk,account=account_name,freshness="FRESH",age_str=age)
            if not send: return TrendPulseDispatchResult(scan.symbol,signal,scan,trade,message,False,"READY_TO_SEND",account_name)
            send_message(message,self._config()); self.runtime.gate.accept(signal,symbol=scan.symbol,now=current); self.database.record_signal_send(key,current.isoformat(),(current+pd.Timedelta(hours=1)).isoformat()); self.accounts[account_name]=register_trade(account,planned_risk=trade.planned_risk)
            self.database.save_account(account_name,balance=self.accounts[account_name].balance,trades_today=self.accounts[account_name].trades_today,planned_risk_used=self.accounts[account_name].planned_risk_used,reset_date=current.date().isoformat())
        return TrendPulseDispatchResult(scan.symbol,signal,scan,trade,message,True,"SENT_AND_ACCEPTED",account_name)
    def scan_and_dispatch(self,symbol:str,*,now:pd.Timestamp|None=None,period:str="30d",send:bool=True,account_name:str=DEFAULT_ACCOUNT)->TrendPulseDispatchResult:
        return self.dispatch_result(self.runtime.scan_symbol(symbol,now=now,period=period),now=now,send=send,account_name=account_name)
    def scan_universe_and_dispatch(self,*,now:pd.Timestamp|None=None,period:str="30d",send:bool=True,account_name:str=DEFAULT_ACCOUNT)->list[TrendPulseDispatchResult]:
        return [self.dispatch_result(x,now=now,send=send,account_name=account_name) for x in self.runtime.scan_universe(now=now,period=period)]
