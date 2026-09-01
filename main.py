"""Complete MULTIBOT2 application runtime."""
from __future__ import annotations
import json,logging,os,threading,time
from wsgiref.simple_server import make_server
from urllib import parse,request
import pandas as pd
from config import ACCOUNT_NAMES,ACCOUNT_SIZE_INR,ACCOUNT_TRADE_LIMITS,IST_TIMEZONE,NSE_15_SYMBOLS,RISK_PER_TRADE_INR,settings,validate_configuration
from db import DatabaseManager
from reminders import ReminderService
from trendpulse_runtime import TrendPulseRuntime
from trendpulse_service import TrendPulseService
from sweep_service import SweepService
from trading import AccountState
from yahoo_provider import YahooProvider
logging.basicConfig(level=logging.INFO,format="%(asctime)s | %(levelname)s | %(message)s");logger=logging.getLogger("multibot2")
DB=DatabaseManager(settings.db_path);ACCOUNTS={};ACTIVE=[];HISTORY=[];SIGNALS=[];RUNTIME=None;TREND=None;SWEEP=None;REMINDERS=None;STOP=threading.Event();LOCK=threading.RLock()
def now():return pd.Timestamp.now(tz=IST_TIMEZONE)
def build_market_data_provider()->YahooProvider:validate_runtime_configuration();return YahooProvider()
def validate_runtime_configuration():
    validate_configuration()
    if settings.timezone!=IST_TIMEZONE or settings.timeframe!="1h" or settings.market_data_provider!="yahoo" or settings.freshness_hours!=1:raise ValueError("Locked MULTIBOT2 runtime configuration violated")
def init_state():
    global ACCOUNTS,ACTIVE,HISTORY
    rows=DB.load_accounts(ACCOUNT_NAMES,ACCOUNT_SIZE_INR,now().date().isoformat());ACCOUNTS={n:AccountState(n,float(rows[n]["starting_balance"]),float(rows[n]["balance"]),float(rows[n]["planned_risk_used"]),int(rows[n]["trades_today"])) for n in ACCOUNT_NAMES};ACTIVE=DB.load_trades("OPEN");HISTORY=DB.load_trades("CLOSED")
def ensure_runtime():
    global RUNTIME,TREND,SWEEP,REMINDERS
    validate_runtime_configuration()
    if not ACCOUNTS:init_state()
    if RUNTIME is None:RUNTIME=TrendPulseRuntime(provider=build_market_data_provider())
    if TREND is None:TREND=TrendPulseService(runtime=RUNTIME,database=DB,accounts=ACCOUNTS)
    if SWEEP is None:SWEEP=SweepService(runtime=RUNTIME,database=DB,accounts=ACCOUNTS)
    if REMINDERS is None:REMINDERS=ReminderService(DB)
def persist_account(a):DB.save_account(a.name,balance=a.balance,trades_today=a.trades_today,planned_risk_used=a.planned_risk_used,reset_date=now().date().isoformat())
def trade_row(result):
    p=result.trade.plan;return {"id":f"{result.account}_{result.symbol}_{int(time.time()*1000)}","status":"OPEN","symbol":result.symbol,"account":result.account,"strategy":p.strategy,"type":p.side,"entry":p.entry,"sl":p.stop_loss,"tp":p.take_profit,"qty":result.trade.quantity,"signal_ts":p.signal_timestamp.isoformat(),"opened_at":now().isoformat()}
def record_result(result):
    if not result.sent:return
    row=trade_row(result);ACTIVE.append(row);DB.save_trade(row["id"],"OPEN",row,row["opened_at"]);persist_account((TREND.accounts if result.account=="nifty" else SWEEP.accounts)[result.account])
def run_trendpulse_cycle(*,now_at=None,send=True,period="30d"):
    ensure_runtime();results=TREND.scan_universe_and_dispatch(now=now_at,period=period,send=send,account_name="nifty")
    for r in results:
        if r.signal.signal in ("BUY","SELL"):SIGNALS.append({"strategy":r.signal.strategy,"symbol":r.symbol,"signal":r.signal.signal,"timestamp":r.signal.timestamp.isoformat(),"reason":r.signal.reason});record_result(r)
    return results
def run_sweep_cycle(*,now_at=None,send=True,period="30d"):
    ensure_runtime();results=SWEEP.scan_universe_and_dispatch(now=now_at,period=period,send=send)
    for r in results:
        if r.signal.signal in ("BUY","SELL"):SIGNALS.append({"strategy":r.signal.strategy,"symbol":r.symbol,"signal":r.signal.signal,"timestamp":r.signal.timestamp.isoformat(),"reason":r.signal.reason});record_result(r)
    return results
def _price(symbol):
    try:data=RUNTIME.provider.fetch(f"{symbol}.NS",period="1d",interval="1m",validate_hourly=False);return None if data.empty else float(data.close.iloc[-1])
    except Exception:return None
def monitor_once():
    for row in list(ACTIVE):
        live=_price(row["symbol"])
        if live is None:continue
        long=row["type"]=="BUY";hit_tp=live>=row["tp"] if long else live<=row["tp"];hit_sl=live<=row["sl"] if long else live>=row["sl"]
        if not(hit_tp or hit_sl):continue
        pnl=(live-row["entry"])*row["qty"] if long else (row["entry"]-live)*row["qty"];row.update(status="CLOSED",exit_price=live,pnl=pnl,exit_reason="TP" if hit_tp else "SL",closed_at=now().isoformat());ACTIVE.remove(row);HISTORY.insert(0,row);DB.save_trade(row["id"],"CLOSED",row,row["closed_at"]);a=ACCOUNTS[row["account"]];ACCOUNTS[row["account"]]=AccountState(a.name,a.starting_balance,a.balance+pnl,a.planned_risk_used,a.trades_today);persist_account(ACCOUNTS[row["account"]])
def scanner_loop():
    while not STOP.is_set():
        try:
            if now().weekday()<5:run_trendpulse_cycle(send=True);run_sweep_cycle(send=True)
        except Exception:logger.exception("scanner cycle failed")
        STOP.wait(settings.scan_interval_seconds)
def monitor_loop():
    while not STOP.is_set():
        try:monitor_once()
        except Exception:logger.exception("monitor cycle failed")
        STOP.wait(settings.monitor_interval_seconds)
def snapshot():
    ensure_runtime()
    with LOCK:
        account_rows=[{"name":a.name,"starting_balance":a.starting_balance,"balance":a.balance,"planned_risk_used":a.planned_risk_used,"daily_trade_limit":a.daily_trade_limit,"max_daily_planned_risk":a.max_daily_planned_risk,"trades_today":a.trades_today,"remaining_trades":a.remaining_trades,"remaining_planned_risk":a.remaining_planned_risk} for a in ACCOUNTS.values()]
        return {"system":{"status":"ONLINE","mode":"PAPER","timezone":IST_TIMEZONE,"timeframe":"1h","leverage":1},"rules":{"account_size_inr":ACCOUNT_SIZE_INR,"risk_per_trade_inr":RISK_PER_TRADE_INR,"account_trade_limits":dict(ACCOUNT_TRADE_LIMITS),"signal_freshness_hours":1},"universe":{"count":15,"symbols":list(NSE_15_SYMBOLS),"fixed":True},"accounts":{"count":4,"names":list(ACCOUNT_NAMES),"data":account_rows},"signals":list(reversed(SIGNALS[-500:])),"trades":ACTIVE+HISTORY[:200],"counts":{"signals":len(SIGNALS),"trades":len(ACTIVE)+len(HISTORY),"open_trades":len(ACTIVE),"closed_trades":len(HISTORY)},"generated_at":now().isoformat()}
def web_server():
    root=os.path.dirname(__file__);files={"/":("dashboard.html","text/html; charset=utf-8"),"/app.js":("app.js","application/javascript"),"/styles.css":("styles.css","text/css")}
    def app(env,start):
        path=env.get("PATH_INFO","/")
        if path in ("/ping","/api/health"):
            body=(b"pong" if path=="/ping" else json.dumps({"ok":True,"status":"ONLINE","timestamp":now().isoformat()}).encode());typ="text/plain" if path=="/ping" else "application/json"
        elif path=="/api/dashboard":body=json.dumps(snapshot(),default=str).encode();typ="application/json"
        elif path in files:
            name,typ=files[path]
            try:body=open(os.path.join(root,name),"rb").read()
            except OSError:start("404 Not Found",[("Content-Type","text/plain")]);return [b"Not found"]
        else:start("404 Not Found",[("Content-Type","text/plain")]);return [b"Not found"]
        start("200 OK",[("Content-Type",typ),("Cache-Control","no-store")]);return [body]
    make_server("0.0.0.0",int(os.getenv("PORT","10000")),app).serve_forever()
def telegram_commands():
    token=settings.telegram_bot_token
    if not token:return
    offset=0
    while not STOP.is_set():
        try:
            req=request.Request(f"https://api.telegram.org/bot{token}/getUpdates",data=parse.urlencode({"timeout":20,"offset":offset}).encode(),method="POST")
            with request.urlopen(req,timeout=30) as r:data=json.loads(r.read())
            for u in data.get("result",[]):
                offset=u["update_id"]+1;m=u.get("message",{});chat=m.get("chat",{}).get("id");cmd=str(m.get("text","")).split()[0].split("@")[0].lower() if m.get("text") else ""
                if not chat:continue
                if cmd=="/start":text="🤖 MULTIBOT2\n/check · /balance · /summary · /risk · /stats"
                elif cmd=="/check":threading.Thread(target=lambda:run_trendpulse_cycle(send=True),daemon=True).start();text="🔍 Scan started."
                elif cmd=="/balance":text="\n".join(f"{a.name}: ₹{a.balance:,.2f} | {a.trades_today}/{a.daily_trade_limit}" for a in ACCOUNTS.values())
                elif cmd=="/summary":text=f"Open trades: {len(ACTIVE)}\nClosed trades: {len(HISTORY)}"
                elif cmd=="/risk":text=f"Open planned risk: ₹{sum(abs(float(x['entry'])-float(x['sl']))*float(x['qty']) for x in ACTIVE):,.2f}"
                elif cmd=="/stats":text=f"Trades: {len(HISTORY)}\nP/L: ₹{sum(float(x.get('pnl',0)) for x in HISTORY):,.2f}"
                else:continue
                request.urlopen(request.Request(f"https://api.telegram.org/bot{token}/sendMessage",data=parse.urlencode({"chat_id":chat,"text":text}).encode(),method="POST"),timeout=15).read()
        except Exception:STOP.wait(5)
def main():
    ensure_runtime();threading.Thread(target=web_server,daemon=True,name="dashboard").start();threading.Thread(target=scanner_loop,daemon=True,name="scanner").start();threading.Thread(target=monitor_loop,daemon=True,name="monitor").start();threading.Thread(target=telegram_commands,daemon=True,name="telegram").start();REMINDERS.start();logger.info("MULTIBOT2 started: NSE-15, Yahoo, 1H, 1h freshness, paper mode")
    while True:time.sleep(3600)
if __name__=="__main__":main()
