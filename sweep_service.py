"""Sweep runtime using the verified original candle/schedule rules.

Sweep has no FVG condition. Neutral notifications are emitted only by Sweep's
scheduled checks; TrendPulse remains silent on neutral scans.
"""
from __future__ import annotations
from dataclasses import dataclass
from threading import Event,RLock,Thread
import pandas as pd
from config import ACCOUNT_SIZE_INR,ACCOUNT_NAMES,IST_TIMEZONE,NSE_15_SYMBOLS,RISK_PER_TRADE_INR
from db import DatabaseManager
from signal_gate import SignalGate
from strategies import StrategySignal
from sweep_engine import detect_sweep
from telegram import TelegramConfig,TelegramMessage,render_signal_message,send_message,signal_rejection_message
from trading import AccountState,PaperTrade,TradePlan,can_open_trade,register_trade
from trendpulse_runtime import TrendPulseRuntime
CRYPTO_SYMBOLS=("BTC-USD",)
FOREX_GOLD_SYMBOLS=("GC=F","EURUSD=X","GBPUSD=X","USDJPY=X","USDCHF=X","AUDUSD=X","USDCAD=X","NZDUSD=X")
NIFTY_SYMBOLS=("^NSEI","^NSEBANK")
CHECK_TIMES={"CRYPTO":((1,30),(5,30),(9,30),(13,30),(17,30),(21,30)),"FOREX_GOLD":((2,30),(6,30),(10,30),(14,30),(18,30),(22,30))}
@dataclass(frozen=True)
class SweepDispatchResult:
    symbol:str;signal:StrategySignal;trade:PaperTrade|None;message:TelegramMessage|None;sent:bool;reason:str;account:str="sweep_4h"
class SweepService:
    DEFAULT_ACCOUNT="sweep_4h"
    def __init__(self,*,runtime=None,telegram_config=None,database=None,accounts=None):
        self.runtime=runtime or TrendPulseRuntime();self.telegram_config=telegram_config;self.database=database or DatabaseManager();self.gate=SignalGate();self._lock=RLock();self._stop=Event();self.last_checks={}
        if accounts is not None:self.accounts=accounts
        else:
            rows=self.database.load_accounts(ACCOUNT_NAMES,ACCOUNT_SIZE_INR,pd.Timestamp.now(tz=IST_TIMEZONE).date().isoformat());self.accounts={n:AccountState(n,float(rows[n]["starting_balance"]),float(rows[n]["balance"]),float(rows[n]["planned_risk_used"]),int(rows[n]["trades_today"])) for n in ACCOUNT_NAMES}
        self._scheduler=Thread(target=self._schedule_loop,daemon=True,name="multibot2-sweep-scheduler");self._scheduler.start()
    def _config(self):return self.telegram_config or TelegramConfig.from_env()
    def _send(self,msg):
        try:send_message(msg,self._config())
        except Exception:pass
    def _checking_message(self,market,timeframe,check_time):
        return TelegramMessage("MSG-SWEEP-CHECK-V1",f"🔎 *SWEEP CHECKING*\n━━━━━━━━━━━━━━━━━━━━━━\n🌐 *Market:* `{market}`\n⏱ *Timeframe:* `{timeframe}`\n🕐 *Check:* `{check_time} IST`\n🟢 *Sweep engine:* `RUNNING`\n🔍 *Checking now...*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    def _neutral_message(self,symbol,result,now):
        age=max(0,int((now-result.candle_end).total_seconds()/60));age_text=f"{age} min ago" if age<60 else f"{age//60} hr {age%60} min ago";fresh=age<=60;icon="✅" if fresh else "⚠️";asset={"BTC-USD":"Bitcoin (BTC)","GC=F":"Gold (XAU/USD)","^NSEI":"NIFTY 50","^NSEBANK":"BANK NIFTY"}.get(symbol,symbol.replace("=X","").replace(".NS",""));market="Crypto" if symbol=="BTC-USD" else "Forex / Gold" if symbol in FOREX_GOLD_SYMBOLS else "NSE"
        return TelegramMessage("MSG-SWEEP-NEUTRAL-V1",f"🟡 *SWEEP · {asset}* · {icon}\n━━━━━━━━━━━━━━━━━━━━━━\n🪙 *Asset:* `{asset}` (`{symbol}`)\n🌐 *Market:* `{market}`\n📊 *Direction:* 🟡 NEUTRAL\n⏱ *Timeframe:* `{result.timeframe}`\n⏳ *Signal Status:* `{('FRESH' if fresh else 'STALE')}` ({age_text})\n⏰ *Candle Closed:* `{result.candle_end.strftime('%d-%b-%Y %H:%M IST')}`\n━━━━━━━━━━━━━━━━━━━━━━\n🎯 *Action:* `INFORMATIONAL — NO PAPER TRADE`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    def _signal(self,symbol,result,now):
        direction="BUY" if result.direction=="BULLISH" else "SELL";signal=StrategySignal("Sweep V2",direction,result.candle_end,result.direction);entry=self._price(symbol)
        if entry is None:return
        sl=result.current["low"] if direction=="BUY" else result.current["high"];distance=entry-sl if direction=="BUY" else sl-entry
        if distance<=0:return
        tp=entry+2*distance if direction=="BUY" else entry-2*distance;qty=RISK_PER_TRADE_INR/distance;account="nifty" if symbol in NIFTY_SYMBOLS or symbol.endswith('.NS') else "sweep_4h";age=max(0,int((now-result.candle_end).total_seconds()/60));age_text=f"{age} min ago" if age<60 else f"{age//60} hr {age%60} min ago";freshness="FRESH" if age<=60 else "STALE";market="Crypto" if symbol=="BTC-USD" else "Forex / Gold" if symbol in FOREX_GOLD_SYMBOLS else "NSE";asset={"BTC-USD":"Bitcoin (BTC)","GC=F":"Gold (XAU/USD)","^NSEI":"NIFTY 50","^NSEBANK":"BANK NIFTY"}.get(symbol,symbol.replace('.NS',''));msg=render_signal_message(signal,symbol=symbol,asset=asset,market=market,timeframe=result.timeframe,entry=entry,stop_loss=sl,take_profit=tp,quantity=qty,risk=RISK_PER_TRADE_INR,account=account,freshness=freshness,age_str=age_text);msg=TelegramMessage(msg.message_type,msg.text.replace("Sweep V2","Sweep"));self._send(msg)
    def _price(self,symbol):
        try:
            data=self.runtime.provider.fetch(symbol,period="2d",interval="1m",validate_hourly=False);return None if data.empty else float(data.close.iloc[-1])
        except Exception:return None
    def _fetch(self,symbol,period="30d"):
        return self.runtime.fetch_symbol_1h(symbol,period=period) if symbol.endswith('.NS') else self.runtime.provider.fetch(symbol,period=period,interval="1h",validate_hourly=False)
    def _scan_one(self,symbol,now,send_neutral=True):
        result=detect_sweep(self._fetch(symbol),symbol,now)
        if result is None:return None
        if result.direction=="NEUTRAL":
            if send_neutral:self._send(self._neutral_message(symbol,result,now))
        else:self._signal(symbol,result,now)
        return result
    def _schedule_loop(self):
        seen=set()
        while not self._stop.is_set():
            try:
                now=pd.Timestamp.now(tz=IST_TIMEZONE);key=now.strftime('%Y-%m-%d %H:%M')
                for market,times in CHECK_TIMES.items():
                    if (now.hour,now.minute) in times and (market,key) not in seen:
                        seen.add((market,key));self.last_checks[market]=now.isoformat();self._send(self._checking_message("Crypto / BTC" if market=="CRYPTO" else "Forex / Gold","4H",now.strftime('%H:%M')))
                        for symbol in (CRYPTO_SYMBOLS if market=="CRYPTO" else FOREX_GOLD_SYMBOLS):
                            try:self._scan_one(symbol,now,True)
                            except Exception:pass
                if now.minute==15 and 10<=now.hour<=15:
                    key2=("NIFTY",key)
                    if key2 not in seen:
                        seen.add(key2)
                        for symbol in NIFTY_SYMBOLS:
                            try:self._scan_one(symbol,now,True)
                            except Exception:pass
                if now.minute==15 and now.hour in (13,15):
                    key3=("NSE",key)
                    if key3 not in seen:
                        seen.add(key3)
                        for symbol in NSE_15_SYMBOLS:
                            try:self._scan_one(symbol,now,True)
                            except Exception:pass
                if len(seen)>500:seen=set(list(seen)[-100:])
            except Exception:pass
            self._stop.wait(20)
    def scan_symbol(self,symbol,*,period="30d"):
        symbol=symbol.strip().upper();frame=self._fetch(symbol,period);result=detect_sweep(frame,symbol,pd.Timestamp.now(tz=IST_TIMEZONE));ts=result.candle_end if result else (frame.index[-1] if len(frame) else pd.Timestamp.now(tz=IST_TIMEZONE));direction={"BULLISH":"BUY","BEARISH":"SELL","NEUTRAL":"NEUTRAL"}.get(result.direction if result else "","NO_SIGNAL");return StrategySignal("Sweep V2",direction,ts,result.direction if result else "NO_SIGNAL"),frame
    def dispatch(self,symbol,signal,candles_1h,*,current_price,now=None,send=True,account_name=DEFAULT_ACCOUNT):
        current=pd.Timestamp.now(tz=IST_TIMEZONE) if now is None else pd.Timestamp(now);current=current.tz_convert(IST_TIMEZONE)
        if signal.signal not in ("BUY","SELL"):return SweepDispatchResult(symbol,signal,None,None,False,"NO_DIRECTIONAL_SIGNAL",account_name)
        if not self.gate.is_fresh(signal,now=current):return self._reject(symbol,signal,"STALE_SIGNAL",account_name=account_name,send=send)
        key=self.gate.signal_key(signal,symbol=symbol)
        with self._lock:
            count=self.database.signal_count(key)
            if count>=2:return self._reject(symbol,signal,"DUPLICATE_SIGNAL_LIMIT",account_name=account_name,send=send)
            if count==1:return self._reject(symbol,signal,"REMINDER_PENDING",account_name=account_name,send=send)
            account=self.accounts[account_name]
            if not can_open_trade(account):return self._reject(symbol,signal,"ACCOUNT_DAILY_LIMIT",account_name=account_name,send=send)
            candle=candles_1h.iloc[-1];entry=float(current_price);sl=float(candle.low) if signal.signal=="BUY" else float(candle.high);distance=entry-sl if signal.signal=="BUY" else sl-entry
            if distance<=0:return self._reject(symbol,signal,"INVALID_SWEEP_RISK",account_name=account_name,send=send)
            tp=entry+2*distance if signal.signal=="BUY" else entry-2*distance;qty=RISK_PER_TRADE_INR/distance;trade=PaperTrade(TradePlan("Sweep",signal.signal,signal.timestamp,entry,sl,tp),account_name,qty);age=max(0,int((current-signal.timestamp).total_seconds()/60));age_text=f"{age} min ago" if age<60 else f"{age//60} hr {age%60} min ago";market="Crypto" if symbol=="BTC-USD" else "Forex / Gold" if symbol in FOREX_GOLD_SYMBOLS else "NSE";asset=symbol.replace('.NS','');msg=render_signal_message(StrategySignal("Sweep V2",signal.signal,signal.timestamp,signal.reason),symbol=symbol,asset=asset,market=market,timeframe="4H" if account_name=="sweep_4h" else "1H",entry=entry,stop_loss=sl,take_profit=tp,quantity=qty,risk=trade.planned_risk,account=account_name,freshness="FRESH" if age<=60 else "STALE",age_str=age_text);msg=TelegramMessage(msg.message_type,msg.text.replace("Sweep V2","Sweep"))
            if send:
                self._send(msg);self.gate.accept(signal,symbol=symbol,now=current);self.database.record_signal_send(key,current.isoformat(),(current+pd.Timedelta(hours=1)).isoformat(),msg.text,{"strategy":"Sweep","symbol":symbol,"direction":signal.signal,"timestamp":signal.timestamp.isoformat()});updated=register_trade(account,planned_risk=min(trade.planned_risk,RISK_PER_TRADE_INR));self.accounts[account_name]=updated;self.database.save_account(account_name,balance=updated.balance,trades_today=updated.trades_today,planned_risk_used=updated.planned_risk_used,reset_date=current.date().isoformat())
            return SweepDispatchResult(symbol,signal,trade,msg,send,"SENT_AND_ACCEPTED" if send else "READY_TO_SEND",account_name)
    def _reject(self,symbol,signal,reason,*,send=True,account_name=DEFAULT_ACCOUNT):
        msg=signal_rejection_message(strategy="Sweep",symbol=symbol,reason=reason)
        if send:self._send(msg)
        return SweepDispatchResult(symbol,signal,None,msg if send else None,False,reason,account_name)
    def scan_universe_and_dispatch(self,*,now=None,period="30d",send=True):
        out=[];current=pd.Timestamp.now(tz=IST_TIMEZONE) if now is None else pd.Timestamp(now)
        for symbol in NSE_15_SYMBOLS:
            try:
                signal,frame=self.scan_symbol(symbol,period=period)
                if signal.signal in ("NO_SIGNAL","NEUTRAL"):continue
                price=self._price(symbol+'.NS')
                if price is not None:out.append(self.dispatch(symbol,signal,frame,current_price=price,now=current,send=send,account_name="sweep_4h"))
            except Exception:continue
        return out
    def stop(self):self._stop.set()
__all__=["SweepDispatchResult","SweepService"]
