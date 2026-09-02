"""Complete Telegram message and transport layer for MULTIBOT2."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
import os
from typing import Mapping
from urllib import parse, request
import pandas as pd
from strategies import StrategySignal
from trading import PaperTrade
BR="━━━━━━━━━━━━━━━━━━━━━━"; BR2="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
DASHBOARD_URL=os.getenv("DASHBOARD_URL","https://multibot2-t74l.onrender.com/dashboard")
class TelegramConfigurationError(RuntimeError): pass
class TelegramTemplateError(RuntimeError): pass
@dataclass(frozen=True)
class TelegramConfig:
    bot_token:str; chat_id:str
    @classmethod
    def from_env(cls):
        token=os.getenv("TELEGRAM_BOT_TOKEN"); chat_id=os.getenv("TELEGRAM_CHAT_ID")
        if not token: raise TelegramConfigurationError("TELEGRAM_BOT_TOKEN is not configured")
        if not chat_id: raise TelegramConfigurationError("TELEGRAM_CHAT_ID is not configured")
        return cls(token,chat_id)
@dataclass(frozen=True)
class TelegramMessage: message_type:str; text:str
APPROVED_TEMPLATES={
"MSG-SWEEP-BUY-V1":"""🟢 *{header_title}* · {status_icon}\n{BR}\n🪙 *Asset:* `{asset}` (`{symbol}`)\n🌐 *Market:* {market}\n📊 *Direction:* LONG 📈\n⏱ *Timeframe:* {timeframe}\n{BR}\n⏳ *Signal Status:* `{status_tag}` ({age_str})\n⏰ *Candle Closed:* `{time_str}`\n{BR}\n💼 *PAPER TRADE EXECUTED*\n{BR}\n🏢 *Account:* `{account}`\n📍 *Entry:* `{currency}{entry_fmt}`\n🛑 *Stop Loss:* `{currency}{stop_loss_fmt}`\n🎯 *Take Profit:* `{currency}{take_profit_fmt}`\n📦 *Quantity:* `{quantity_fmt}`\n💸 *Risk:* `₹{risk_fmt}`\n{BR}\nℹ️ _✅ FRESH = Closed ≤1h ago | ⚠️ STALE = Closed >1h ago_\n{BR2}""",
"MSG-SWEEP-SELL-V1":"""🔴 *{header_title}* · {status_icon}\n{BR}\n🪙 *Asset:* `{asset}` (`{symbol}`)\n🌐 *Market:* {market}\n📊 *Direction:* SHORT 📉\n⏱ *Timeframe:* {timeframe}\n{BR}\n⏳ *Signal Status:* `{status_tag}` ({age_str})\n⏰ *Candle Closed:* `{time_str}`\n{BR}\n💼 *PAPER TRADE EXECUTED*\n{BR}\n🏢 *Account:* `{account}`\n📍 *Entry:* `{currency}{entry_fmt}`\n🛑 *Stop Loss:* `{currency}{stop_loss_fmt}`\n🎯 *Take Profit:* `{currency}{take_profit_fmt}`\n📦 *Quantity:* `{quantity_fmt}`\n💸 *Risk:* `₹{risk_fmt}`\n{BR}\nℹ️ _✅ FRESH = Closed ≤1h ago | ⚠️ STALE = Closed >1h ago_\n{BR2}""",
"MSG-TRENDPULSE-BUY-V1":"""🟢 *{header_title}* · {status_icon}\n{BR}\n🪙 *Asset:* `{asset}` (`{symbol}`)\n🌐 *Market:* {market}\n📊 *Direction:* LONG 📈\n⏱ *Timeframe:* {timeframe}\n{BR}\n⏳ *Signal Status:* `{status_tag}` ({age_str})\n⏰ *Candle Closed:* `{time_str}`\n{BR}\n💼 *PAPER TRADE EXECUTED*\n{BR}\n🏢 *Account:* `{account}`\n📍 *Entry:* `{currency}{entry_fmt}`\n🛑 *Stop Loss:* `{currency}{stop_loss_fmt}`\n🎯 *Take Profit:* `{currency}{take_profit_fmt}`\n📦 *Quantity:* `{quantity_fmt}`\n💸 *Risk:* `₹{risk_fmt}`\n{BR}\nℹ️ _✅ FRESH = Closed ≤1h ago | ⚠️ STALE = Closed >1h ago_\n{BR2}""",
"MSG-TRENDPULSE-SELL-V1":"""🔴 *{header_title}* · {status_icon}\n{BR}\n🪙 *Asset:* `{asset}` (`{symbol}`)\n🌐 *Market:* {market}\n📊 *Direction:* SHORT 📉\n⏱ *Timeframe:* {timeframe}\n{BR}\n⏳ *Signal Status:* `{status_tag}` ({age_str})\n⏰ *Candle Closed:* `{time_str}`\n{BR}\n💼 *PAPER TRADE EXECUTED*\n{BR}\n🏢 *Account:* `{account}`\n📍 *Entry:* `{currency}{entry_fmt}`\n🛑 *Stop Loss:* `{currency}{stop_loss_fmt}`\n🎯 *Take Profit:* `{currency}{take_profit_fmt}`\n📦 *Quantity:* `{quantity_fmt}`\n💸 *Risk:* `₹{risk_fmt}`\n{BR}\nℹ️ _✅ FRESH = Closed ≤1h ago | ⚠️ STALE = Closed >1h ago_\n{BR2}"""}
SWEEP_MESSAGE_TYPES={"BUY":"MSG-SWEEP-BUY-V1","SELL":"MSG-SWEEP-SELL-V1"}; TRENDPULSE_MESSAGE_TYPES={"BUY":"MSG-TRENDPULSE-BUY-V1","SELL":"MSG-TRENDPULSE-SELL-V1"}
def signal_message_type(signal):
    mapping=SWEEP_MESSAGE_TYPES if signal.strategy=="Sweep V2" else TRENDPULSE_MESSAGE_TYPES if signal.strategy=="TrendPulse" else None
    if mapping is None or signal.signal not in mapping: raise TelegramTemplateError(f"No approved Telegram template for {signal.strategy}/{signal.signal}")
    return mapping[signal.signal]
def _currency(symbol): return "₹" if symbol.endswith(".NS") or "NSE" in symbol or symbol in {"^NSEI","^NSEBANK"} else "$"
def _display_name(symbol,asset=""):
    if asset:return asset
    return {"BTC-USD":"Bitcoin (BTC)","GC=F":"Gold (XAU/USD)","SI=F":"Silver (XAG/USD)","HG=F":"Copper","^NSEI":"NIFTY 50","^NSEBANK":"BANK NIFTY"}.get(symbol,symbol.replace(".NS",""))
def _price_decimals(symbol):
    if symbol=="BTC-USD":return 2
    if symbol=="USDJPY=X":return 3
    if symbol.endswith("=X"):return 5
    return 2
def build_signal_fields(signal:StrategySignal,**fields):
    symbol=fields.get("symbol","") or ""; asset=_display_name(symbol,fields.get("asset","") or ""); d=_price_decimals(symbol); freshness=fields.get("freshness") or "FRESH"
    return {"BR":BR,"BR2":BR2,"asset":asset,"symbol":symbol,"market":fields.get("market","NSE"),"timeframe":fields.get("timeframe","1H"),"account":str(fields.get("account","")).upper(),"status_tag":freshness,"status_icon":"⚠️" if "STALE" in freshness else "✅","age_str":fields.get("age_str","") or "","header_title":f"{signal.strategy} · {asset}","time_str":signal.timestamp.strftime("%d-%b-%Y %H:%M IST"),"currency":_currency(symbol),"entry_fmt":f"{float(fields.get('entry') if fields.get('entry') is not None else signal.entry or 0):,.{d}f}","stop_loss_fmt":f"{float(fields.get('stop_loss') or 0):,.{d}f}","take_profit_fmt":f"{float(fields.get('take_profit') or 0):,.{d}f}","quantity_fmt":f"{float(fields.get('quantity') or 0):.4f}","risk_fmt":f"{float(fields.get('risk') or 0):,.2f}"}
def render_template(message_type,fields):
    try:return TelegramMessage(message_type,APPROVED_TEMPLATES[message_type].format_map(fields))
    except KeyError as exc: raise TelegramTemplateError(f"Template requires unavailable field: {exc.args[0]}") from exc
def render_signal_message(signal,**fields):return render_template(signal_message_type(signal),build_signal_fields(signal,**fields))
def build_trade_fields(trade:PaperTrade):
    p=trade.plan; return {"strategy":p.strategy,"side":p.side,"signal_timestamp":p.signal_timestamp.isoformat(),"entry":p.entry,"stop_loss":p.stop_loss,"take_profit":p.take_profit,"risk_per_unit":p.risk_per_unit,"status":trade.status,"exit_price":trade.exit_price if trade.exit_price is not None else "","exit_timestamp":trade.exit_timestamp.isoformat() if trade.exit_timestamp is not None else "","exit_reason":trade.exit_reason or ""}
def signal_rejection_message(*,strategy,symbol,reason,detail=""):
    labels={"STALE_SIGNAL":"⏳ Signal is older than the 1-hour freshness limit.","DUPLICATE_SIGNAL_LIMIT":"🔁 This signal has already reached its allowed send limit.","REMINDER_PENDING":"🔔 This signal was already sent and is waiting for its one-hour reminder.","ACCOUNT_DAILY_LIMIT":"🛑 The account has reached its locked daily trade limit.","MISSING_SIGNAL_CANDLE":"🕯️ The required 1H signal candle is unavailable.","INVALID_SWEEP_RISK":"⚠️ Stop-loss distance is invalid, so risk cannot be calculated safely.","NO_DIRECTIONAL_SIGNAL":"💤 The strategy did not produce a BUY or SELL signal."}; explanation=labels.get(reason,detail or "Signal was not dispatched."); extra=f"\n📝 *Detail:* `{detail}`" if detail and detail!=explanation else ""; return TelegramMessage("MSG-SIGNAL-REJECTED-V1",f"⚠️ *SIGNAL NOT SENT*\n{BR}\n🧠 *Strategy:* `{strategy}`\n🪙 *Asset:* `{symbol}`\n🚫 *Reason:* `{reason}`\nℹ️ {explanation}{extra}\n{BR}\n💼 No paper trade was executed.\n{BR2}")
def trade_closed_message(trade,live,pnl,balance,is_long,hit_tp):
    result="🎉 WIN" if hit_tp else "💀 LOSS"; pnl_s=f"+₹{pnl:,.2f}" if pnl>=0 else f"-₹{abs(pnl):,.2f}"; symbol=str(trade.get("symbol","")); name=_display_name(symbol); currency=_currency(symbol); return TelegramMessage("MSG-TRADE-CLOSED-V1",f"{'🟢' if is_long else '🔴'} *TRADE CLOSED — {result}*\n{BR}\n🪙 `{name}` | {'LONG 📈' if is_long else 'SHORT 📉'}\n🎯 *Strategy:* {trade.get('strategy',trade.get('strat','N/A'))}\n🏢 *Account:* `{str(trade.get('account','macro')).upper()}`\n{BR}\n📍 *Entry:* `{currency}{float(trade.get('entry',0)):,.2f}`\n{'🎯' if hit_tp else '🛑'} *Exit:* `{currency}{live:,.2f}`\n🛑 *Stop Loss:* `{currency}{float(trade.get('sl',trade.get('stop_loss',0))):,.2f}`\n🎯 *Take Profit:* `{currency}{float(trade.get('tp',trade.get('take_profit',0))):,.2f}`\n{BR}\n{'💰' if hit_tp else '💸'} *P/L:* `{pnl_s}`\n🏦 *Balance:* `₹{balance:,.2f}`\n{BR2}")
def msg_start():
    return f"🤖 *MAVIS TRADING ENGINE — COMMAND CENTER*\n{BR}\n🟢 *SYSTEM:* ONLINE · PAPER MODE\n📡 *DATA:* Yahoo Finance · 1H\n🇮🇳 *UNIVERSE:* NSE-15\n🛡️ *RISK:* ₹2,000 / trade\n{BR}\n🌐 *DASHBOARD:* {DASHBOARD_URL}\n{BR}\n📊 *OPERATIONAL COMMANDS:*\n├ `/start` / `/menu` — Command guide & status\n├ `/check` / `/scan` — Force immediate scan\n├ `/test` — Test data feeds & latency\n├ `/summary` — Open trades & floating P/L\n├ `/balance` — View virtual account equity\n├ `/stats` — Strategy win-rate & P/L report\n├ `/risk` — Portfolio exposure & 1R metrics\n├ `/weekly` — 7-day performance digest\n├ `/newspause` — Toggle high-impact news pause\n├ `/refreshnews` — Refresh news calendar\n└ `/backtest` — Run strategy backtester\n{BR2}"
def msg_scan_started():return f"🔍 *SCAN STARTED*\n{BR}\n📡 Checking the locked NSE-15 universe on the 1H timeframe...\n⏳ Please wait for the scan result.\n{BR2}"
def msg_scan_result(found,checked):return f"🔎 *SCAN COMPLETE*\n{BR}\n📊 Checked: `{checked}` assets\n🎯 New signals: `{found}`\n{'🟢 Signals dispatched to Telegram.' if found else '💤 No fresh approved signals found.'}\n{BR2}"
def msg_balance(accounts):
    lines=["💰 *VIRTUAL ACCOUNT BALANCE*",BR]
    for name,a in accounts.items(): lines.append(f"{('🌐' if name=='macro' else '🇮🇳' if name=='nifty' else '🇺🇸' if name=='ny_session' else '🔵')} *{name.replace('_',' ').title()}:* `₹{float(a.balance):,.2f}` · `{int(a.trades_today)}/{int(a.daily_trade_limit)}`")
    return "\n".join(lines+[BR2])
def _pnl_value(t):
    try:return float(t.get("pnl",0))
    except Exception:return 0.0
def msg_summary(active,history,live_prices=None):
    live_prices=live_prices or {}; floating=0.0; available=True
    for t in active:
        if t.get("symbol") not in live_prices: available=False; continue
        px=float(live_prices[t["symbol"]]); entry=float(t.get("entry",0)); qty=float(t.get("qty",0)); floating+=(px-entry)*qty if str(t.get("type","")).upper() in {"BUY","LONG"} else (entry-px)*qty
    pnl_text=f"₹{floating:+,.2f}" if available else "— (live price unavailable)"
    return f"📋 *PORTFOLIO SUMMARY*\n{BR}\n🟡 *Open Trades:* `{len(active)}`\n📚 *Closed Trades:* `{len(history)}`\n💹 *Floating P/L:* `{pnl_text}`\n{BR2}"
def msg_risk(active):
    risk=sum(abs(float(t.get("entry",0))-float(t.get("sl",0)))*float(t.get("qty",0)) for t in active); return f"🛡️ *PORTFOLIO RISK*\n{BR}\n🔥 *Open Planned Risk:* `₹{risk:,.2f}`\n📌 *Per-trade risk cap:* `₹2,000.00`\n⚙️ *Leverage:* `1x`\n{BR2}"
def msg_stats(history):
    wins=sum(1 for t in history if str(t.get("exit_reason","")).upper()=="TP" or _pnl_value(t)>0); losses=sum(1 for t in history if _pnl_value(t)<0); pnl=sum(_pnl_value(t) for t in history); total=wins+losses; wr=wins/total*100 if total else 0; return f"📊 *PERFORMANCE STATS*\n{BR}\n📈 *Trades:* `{len(history)}`\n✅ *Wins:* `{wins}`\n❌ *Losses:* `{losses}`\n🎯 *Win Rate:* `{wr:.1f}%`\n💰 *Total P/L:* `{'+' if pnl>=0 else ''}₹{pnl:,.2f}`\n{BR2}"
def msg_weekly(history,now=None):
    current=pd.Timestamp.now(tz="Asia/Kolkata") if now is None else pd.Timestamp(now).tz_convert("Asia/Kolkata"); cutoff=current-pd.Timedelta(days=7); recent=[]
    for t in history:
        raw=t.get("closed_at") or t.get("exit_timestamp") or t.get("time")
        try:
            ts=pd.Timestamp(raw)
            if ts.tzinfo is None: continue
            if ts.tz_convert("Asia/Kolkata")>=cutoff: recent.append(t)
        except Exception: continue
    pnl=sum(_pnl_value(t) for t in recent); wins=sum(1 for t in recent if _pnl_value(t)>0); losses=sum(1 for t in recent if _pnl_value(t)<0); total=wins+losses; wr=wins/total*100 if total else 0
    return f"🗓️ *WEEKLY DIGEST*\n{BR}\n📈 *7-Day P/L:* `{'+' if pnl>=0 else ''}₹{pnl:,.2f}`\n📊 *Trades:* `{total}` · ✅ `{wins}W` · ❌ `{losses}L` · 🎯 `{wr:.1f}%`\n{BR2}"
def msg_test(ok,detail):return f"🧪 *DATA FEED TEST*\n{BR}\n{'🟢' if ok else '🔴'} *Status:* `{'ONLINE' if ok else 'FAILED'}`\n📡 *Yahoo Finance:* {detail}\n⏱️ *Runtime:* 1H\n{BR2}"
def msg_news_pause(enabled):return f"📰 *NEWS PAUSE*\n{BR}\n{'🟡 ENABLED' if enabled else '🟢 DISABLED'}\n{'⏸️ New signal dispatch is paused.' if enabled else '▶️ Normal signal dispatch resumed.'}\n{BR2}"
def msg_news_refresh():return f"📰 *NEWS CALENDAR REFRESH*\n{BR}\n🔄 Refresh requested.\n📡 Runtime will use the configured news source when available.\n{BR2}"
def msg_backtest():return f"📈 *BACKTEST ENGINE*\n{BR}\n🧪 Backtest request received.\n⚙️ Strategy rules remain locked to MULTIBOT2.\n💼 Results are analytical only — no live orders.\n{BR2}"
def msg_error(context,error):return f"⚠️ *ERROR — {context}*\n{BR}\n❌ `{str(error)[:700]}`\n🛡️ Paper mode remains active.\n{BR2}"
def reminder_message(original_text):return TelegramMessage("MSG-REMINDER-V1",f"🔔 *SIGNAL REMINDER*\n{BR}\n{original_text}\n{BR2}")
def send_message(message,config):
    if not message.text.strip(): raise TelegramTemplateError("Cannot send an empty Telegram message")
    payload=parse.urlencode({"chat_id":config.chat_id,"text":message.text,"parse_mode":"Markdown"}).encode(); req=request.Request(f"https://api.telegram.org/bot{config.bot_token}/sendMessage",data=payload,method="POST",headers={"Content-Type":"application/x-www-form-urlencoded"})
    with request.urlopen(req,timeout=15) as response:
        if response.status!=200: raise RuntimeError(f"Telegram API request failed: HTTP {response.status}")
__all__=["TelegramConfig","TelegramMessage","TelegramConfigurationError","TelegramTemplateError","APPROVED_TEMPLATES","signal_message_type","render_signal_message","send_message","signal_rejection_message","trade_closed_message","msg_start","msg_scan_started","msg_scan_result","msg_balance","msg_summary","msg_risk","msg_stats","msg_weekly","msg_test","msg_news_pause","msg_news_refresh","msg_backtest","msg_error","reminder_message","build_trade_fields"]