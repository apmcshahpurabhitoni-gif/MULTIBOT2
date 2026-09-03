"""MULTIBOT2 runtime: one canonical state path for bot, DB and dashboard."""
from __future__ import annotations
import json,logging,os,threading,time
from urllib import parse,request
from wsgiref.simple_server import make_server
import pandas as pd
from backtest import sweep_backtest,trendpulse_backtest
from config import ACCOUNT_NAMES,ACCOUNT_SIZE_INR,ACCOUNT_TRADE_LIMITS,APP_VERSION,BACKTEST_ASSETS,IST_TIMEZONE,LIVE_ASSETS,LIVE_ASSET_MAP,LIVE_SYMBOLS,NSE_15_SYMBOLS,RISK_PER_TRADE_INR,WHAT_IS_NEW,settings,validate_configuration
from dashboard import build_dashboard_snapshot
from db import DatabaseManager
from news import NewsService
from reminders import ReminderService
from sweep_service import SweepService
from telegram import TelegramConfig,TelegramMessage,msg_backtest,msg_balance,msg_error,msg_news_pause,msg_news_refresh,msg_risk,msg_scan_result,msg_scan_started,msg_start,msg_stats,msg_summary,msg_test,msg_weekly,send_message,trade_closed_message
from trading import AccountState
from trendpulse_runtime import TrendPulseRuntime
from trendpulse_service import TrendPulseService
from yahoo_provider import YahooProvider

logging.basicConfig(level=logging.INFO,format="%(asctime)s | %(levelname)s | %(message)s")
logger=logging.getLogger("multibot2")
DB=DatabaseManager(settings.db_path); NEWS=NewsService()
ACCOUNTS={}; ACTIVE=[]; HISTORY=[]; SIGNALS=[]
RUNTIME=None; TREND=None; SWEEP=None; REMINDERS=None
STOP=threading.Event(); LOCK=threading.RLock(); NEWS_PAUSE_ENABLED=False
LAST_SCANS={"trendpulse":{"status":"NOT_RUN","at":None,"checked":0,"directional":0,"sent":0,"errors":0},
            "sweep":{"status":"NOT_RUN","at":None,"checked":0,"directional":0,"sent":0,"errors":0}}

def now(): return pd.Timestamp.now(tz=IST_TIMEZONE)
def validate_runtime_configuration():
    validate_configuration()
    if settings.timezone!=IST_TIMEZONE or settings.timeframe!="1h" or settings.market_data_provider!="yahoo" or settings.freshness_hours!=1:
        raise ValueError("Locked runtime configuration was changed")
def build_market_data_provider(): validate_runtime_configuration(); return YahooProvider()

def init_state():
    global ACCOUNTS,ACTIVE,HISTORY,SIGNALS
    rows=DB.load_accounts(ACCOUNT_NAMES,ACCOUNT_SIZE_INR,now().date().isoformat())
    ACCOUNTS={n:AccountState(n,float(rows[n]["starting_balance"]),float(rows[n]["balance"]),float(rows[n]["planned_risk_used"]),int(rows[n]["trades_today"])) for n in ACCOUNT_NAMES}
    ACTIVE=DB.load_trades("OPEN"); HISTORY=DB.load_trades("CLOSED"); SIGNALS=DB.load_signal_history(500)

def ensure_runtime():
    global RUNTIME,TREND,SWEEP,REMINDERS
    validate_runtime_configuration()
    if not ACCOUNTS: init_state()
    if RUNTIME is None: RUNTIME=TrendPulseRuntime(provider=build_market_data_provider())
    if TREND is None: TREND=TrendPulseService(runtime=RUNTIME,database=DB,accounts=ACCOUNTS)
    if SWEEP is None: SWEEP=SweepService(runtime=RUNTIME,database=DB,accounts=ACCOUNTS)
    if REMINDERS is None and settings.telegram_bot_token and settings.telegram_chat_id: REMINDERS=ReminderService(DB)

def persist_account(account):
    DB.save_account(account.name,balance=account.balance,trades_today=account.trades_today,planned_risk_used=account.planned_risk_used,reset_date=now().date().isoformat())

def trade_row(result):
    plan=result.trade.plan; asset=LIVE_ASSET_MAP[result.symbol]
    return {"id":f"{result.account}_{result.symbol}_{int(time.time()*1000)}","status":"OPEN","symbol":asset.symbol,
            "label":asset.label,"market":asset.market,"asset_type":asset.asset_type,"group":asset.group,
            "timeframe":asset.trendpulse_signal_timeframe if result.signal.strategy=="TrendPulse" else asset.sweep_timeframe,
            "account":result.account,"strategy":plan.strategy,"type":plan.side,"entry":plan.entry,"sl":plan.stop_loss,"tp":plan.take_profit,
            "qty":result.trade.quantity,"risk_per_unit":plan.risk_per_unit,"planned_risk":result.trade.planned_risk,
            "signal_ts":plan.signal_timestamp.isoformat(),"opened_at":now().isoformat()}

def record_result(result):
    """Update dashboard memory after the service has persisted the trade."""
    global ACTIVE, SIGNALS
    if not result.sent or result.trade is None:
        return
    row=trade_row(result)
    trade_id=getattr(result,"trade_id",None)
    if trade_id:
        row["id"]=trade_id
    with LOCK:
        ACTIVE=[r for r in ACTIVE if r["id"]!=row["id"]]
        ACTIVE.insert(0,row)
    SIGNALS=DB.load_signal_history(500)


def run_trendpulse_cycle(*,now_at=None,send=True,period="30d"):
    ensure_runtime()
    results=_run_scan("trendpulse",lambda: TREND.scan_universe_and_dispatch(now=now_at,period=period,send=send,account_name="nifty"))
    for r in results: record_result(r)
    return results

def run_sweep_cycle(*,now_at=None,send=True,period="30d"):
    ensure_runtime()
    results=_run_scan("sweep",lambda: SWEEP.scan_universe_and_dispatch(now=now_at,period=period,send=send))
    for r in results: record_result(r)
    return results

def _price(symbol):
    asset=LIVE_ASSET_MAP.get(symbol)
    if asset is None or RUNTIME is None: return None
    try:
        data=RUNTIME.provider.fetch(asset.yahoo_symbol,period="1d",interval="1m",validate_hourly=False)
        return None if data.empty else float(data.close.iloc[-1])
    except Exception: return None

def monitor_once():
    ensure_runtime()
    for row in list(ACTIVE):
        live=_price(row["symbol"])
        if live is None: continue
        long=row["type"]=="BUY"; hit_tp=live>=row["tp"] if long else live<=row["tp"]; hit_sl=live<=row["sl"] if long else live>=row["sl"]
        if not(hit_tp or hit_sl): continue
        pnl=(live-row["entry"])*row["qty"] if long else (row["entry"]-live)*row["qty"]
        closed=dict(row,status="CLOSED",exit_price=live,pnl=pnl,exit_reason="TP" if hit_tp else "SL",closed_at=now().isoformat())
        with LOCK:
            ACTIVE[:]=[r for r in ACTIVE if r["id"]!=row["id"]]; HISTORY.insert(0,closed)
        DB.save_trade(row["id"],"CLOSED",closed,closed["closed_at"])
        account=ACCOUNTS[row["account"]]
        updated=AccountState(account.name,account.starting_balance,account.balance+pnl,max(0.0,account.planned_risk_used-float(row.get("planned_risk",0))),account.trades_today)
        ACCOUNTS[row["account"]]=updated; persist_account(updated)
        if settings.telegram_bot_token and settings.telegram_chat_id:
            try: send_message(trade_closed_message(closed,live,pnl,updated.balance,long,hit_tp),TelegramConfig.from_env())
            except Exception as exc: logger.warning("trade-close Telegram send failed: %s",exc)

def scanner_loop():
    while not STOP.is_set():
        try:
            if not NEWS_PAUSE_ENABLED:
                run_trendpulse_cycle(send=True); run_sweep_cycle(send=True)
        except Exception: logger.exception("scanner cycle failed")
        STOP.wait(settings.scan_interval_seconds)

def monitor_loop():
    while not STOP.is_set():
        try: monitor_once()
        except Exception: logger.exception("monitor cycle failed")
        STOP.wait(settings.monitor_interval_seconds)

def _backtest_payload(strategy,symbol,period):
    ensure_runtime(); key=strategy.strip().lower().replace(" ",""); symbol=symbol.strip().upper()
    if key not in {"trendpulse","sweepv2","sweep"}: raise ValueError("strategy must be TrendPulse or Sweep V2")
    if symbol not in BACKTEST_ASSETS: raise ValueError("symbol must be a supported backtest asset")
    if period not in {"5d","30d","60d","90d","1y"}: raise ValueError("invalid period")
    asset=LIVE_ASSET_MAP[symbol]
    if key=="trendpulse":
        frame=RUNTIME.fetch_symbol_1h(symbol,period=period); result=trendpulse_backtest(frame,account="nifty")
    else:
        if asset.market=="NSE": interval="1h"
        else:
            if period in {"90d","1y"}: raise ValueError("Sweep V2 global backtests require 5d, 30d or 60d")
            interval="30m"
        frame=RUNTIME.provider.fetch(asset.yahoo_symbol,period=period,interval=interval,validate_hourly=False)
        result=sweep_backtest(frame,symbol=symbol,account="sweep_4h")
    daily={}; rows=[]
    for item in result.signals:
        s=item.signal
        if s.signal not in ("BUY","SELL"): continue
        ts=pd.Timestamp(item.candle_timestamp); ts=ts.tz_localize(IST_TIMEZONE) if ts.tzinfo is None else ts.tz_convert(IST_TIMEZONE)
        day=ts.strftime("%Y-%m-%d"); bucket=daily.setdefault(day,{"buy":0,"sell":0,"total":0}); bucket[s.signal.lower()]+=1; bucket["total"]+=1
        rows.append({"timestamp":s.timestamp.isoformat(),"direction":s.signal,"reason":s.reason,"entry":s.entry})
    return {"ok":True,"strategy":result.strategy,"symbol":symbol,"asset":BACKTEST_ASSETS[symbol],"period":period,
            "account":result.account,"starting_account":result.starting_account,"total_signals":result.total_signals,
            "buy_signals":result.buy_signals,"sell_signals":result.sell_signals,"neutral_signals":result.neutral_signals,
            "trades_taken":result.trades_taken,"planned_risk":result.planned_risk,"candle_count":len(frame),
            "daily":[{"date":d,**v} for d,v in sorted(daily.items())],"signals":rows[-200:],"generated_at":now().isoformat()}

def snapshot():
    if not ACCOUNTS: init_state()
    # Reload durable state for every API request. The dashboard never depends on stale in-memory lists.
    fresh_accounts=DB.load_accounts(ACCOUNT_NAMES,ACCOUNT_SIZE_INR,now().date().isoformat())
    accounts=[AccountState(n,float(fresh_accounts[n]["starting_balance"]),float(fresh_accounts[n]["balance"]),float(fresh_accounts[n]["planned_risk_used"]),int(fresh_accounts[n]["trades_today"])) for n in ACCOUNT_NAMES]
    signals=DB.load_signal_history(500); trades=DB.load_trades()
    scan={"trendpulse":dict(LAST_SCANS["trendpulse"]),"sweep":dict(LAST_SCANS["sweep"])}
    return build_dashboard_snapshot(version=APP_VERSION,whats_new=WHAT_IS_NEW,accounts=accounts,signals=signals,trades=trades,scan=scan,
                                    health={"database":"SUPABASE+SQLITE" if DB.supabase_enabled else "SQLITE_FALLBACK","provider":"YAHOO","telegram":"CONFIGURED" if settings.telegram_bot_token else "DISABLED"})

def _json_response(start,payload,status="200 OK"):
    body=json.dumps(payload,default=str).encode(); start(status,[("Content-Type","application/json"),("Cache-Control","no-store")]); return [body]

def _calendar_payload(query):
    target=query.get("date",[None])[0]; impacts={x.strip().title() for x in query.get("impact",["All"])[0].split(",") if x.strip()} or {"All"}
    if "All" in impacts: impacts={"All"}
    return NEWS.get(target_date=target,impacts=impacts,force=query.get("refresh")==["1"])

def web_server():
    root=os.path.dirname(__file__)
    files={"/":("dashboard.html","text/html; charset=utf-8"),"/dashboard":("dashboard.html","text/html; charset=utf-8"),"/app.js":("app.js","application/javascript"),"/styles.css":("styles.css","text/css")}
    def app(env,start):
        path=env.get("PATH_INFO","/"); query=parse.parse_qs(env.get("QUERY_STRING",""))
        if path in ("/ping","/api/health"):
            if path=="/ping": start("200 OK",[("Content-Type","text/plain"),("Cache-Control","no-store")]); return [b"pong"]
            return _json_response(start,{"ok":True,"status":"ONLINE","timestamp":now().isoformat(),"version":APP_VERSION})
        if path=="/api/dashboard": return _json_response(start,snapshot())
        if path in ("/api/calendar","/api/news"):
            try: return _json_response(start,_calendar_payload(query))
            except Exception as exc: return _json_response(start,{"ok":False,"error":str(exc)},"400 Bad Request")
        if path=="/api/backtest":
            try: return _json_response(start,_backtest_payload(query.get("strategy",["TrendPulse"])[0],query.get("symbol",[next(iter(BACKTEST_ASSETS))])[0],query.get("period",["30d"])[0]))
            except Exception as exc: return _json_response(start,{"ok":False,"error":str(exc)},"400 Bad Request")
        if path in files:
            name,typ=files[path]
            try: body=open(os.path.join(root,name),"rb").read()
            except OSError: start("404 Not Found",[("Content-Type","text/plain")]); return [b"Not found"]
            start("200 OK",[("Content-Type",typ),("Cache-Control","no-store")]); return [body]
        start("404 Not Found",[("Content-Type","text/plain")]); return [b"Not found"]
    make_server("0.0.0.0",int(os.getenv("PORT","10000")),app).serve_forever()

def _send_chat(chat_id,message):
    config=TelegramConfig.from_env(); target=TelegramConfig(config.bot_token,str(chat_id))
    if isinstance(message,str): message=TelegramMessage("MSG-COMMAND-V1",message)
    send_message(message,target)

def _handle_command(chat_id,cmd):
    global NEWS_PAUSE_ENABLED
    try:
        if cmd in ("/start","/menu"): _send_chat(chat_id,msg_start())
        elif cmd in ("/check","/scan"):
            _send_chat(chat_id,msg_scan_started()); trend=run_trendpulse_cycle(send=True); sweep=run_sweep_cycle(send=True)
            _send_chat(chat_id,msg_scan_result(sum(1 for r in trend+sweep if r.sent),len(LIVE_ASSETS)*2))
        elif cmd=="/balance": _send_chat(chat_id,msg_balance(ACCOUNTS))
        elif cmd=="/summary": _send_chat(chat_id,msg_summary(DB.load_trades("OPEN"),DB.load_trades("CLOSED")))
        elif cmd=="/risk": _send_chat(chat_id,msg_risk(DB.load_trades("OPEN")))
        elif cmd=="/stats": _send_chat(chat_id,msg_stats(DB.load_trades("CLOSED")))
        elif cmd=="/weekly": _send_chat(chat_id,msg_weekly(DB.load_trades("CLOSED")))
        elif cmd=="/newspause": NEWS_PAUSE_ENABLED=not NEWS_PAUSE_ENABLED; _send_chat(chat_id,msg_news_pause(NEWS_PAUSE_ENABLED))
        elif cmd=="/refreshnews": NEWS.refresh(); _send_chat(chat_id,msg_news_refresh())
        elif cmd=="/backtest": _send_chat(chat_id,msg_backtest())
        elif cmd=="/test": ensure_runtime(); ok=_price("RELIANCE") is not None; _send_chat(chat_id,msg_test(ok,"RELIANCE price feed responded." if ok else "RELIANCE price feed did not respond."))
    except Exception as exc:
        logger.exception("Telegram command failed")
        try: _send_chat(chat_id,msg_error(f"COMMAND {cmd}",exc))
        except Exception: pass

def telegram_commands():
    token=settings.telegram_bot_token
    if not token: logger.warning("Telegram disabled: TELEGRAM_BOT_TOKEN missing"); return
    offset=0
    while not STOP.is_set():
        try:
            payload=parse.urlencode({"timeout":20,"offset":offset}).encode()
            with request.urlopen(request.Request(f"https://api.telegram.org/bot{token}/getUpdates",data=payload,method="POST"),timeout=30) as response: data=json.loads(response.read())
            for update in data.get("result",[]):
                offset=int(update["update_id"])+1; message=update.get("message",{}); chat_id=message.get("chat",{}).get("id"); text=str(message.get("text","")); cmd=text.split()[0].split("@")[0].lower() if text else ""
                if chat_id and cmd: threading.Thread(target=_handle_command,args=(str(chat_id),cmd),daemon=True).start()
        except Exception as exc: logger.warning("Telegram polling failed: %s",exc); STOP.wait(5)

def main():
    ensure_runtime()
    threading.Thread(target=web_server,daemon=True,name="dashboard").start()
    threading.Thread(target=scanner_loop,daemon=True,name="scanner").start()
    threading.Thread(target=monitor_loop,daemon=True,name="monitor").start()
    if settings.telegram_bot_token and settings.telegram_chat_id:
        threading.Thread(target=telegram_commands,daemon=True,name="telegram").start()
        if REMINDERS is not None: REMINDERS.start()
    logger.info("MULTIBOT2 %s started: 19 assets, Yahoo, TrendPulse 1H+4H, Sweep V2, 1h freshness, paper mode",APP_VERSION)
    while True: time.sleep(3600)
if __name__=="__main__": main()
