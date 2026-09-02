"""Complete MULTIBOT2 application runtime.

The dashboard is presentation-only. Strategy, freshness, risk, execution,
persistence and Telegram rules remain server-side and canonical.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from urllib import parse, request
from wsgiref.simple_server import make_server

import pandas as pd

from backtest import sweep_backtest, trendpulse_backtest
from config import (
    ACCOUNT_NAMES,
    ACCOUNT_SIZE_INR,
    ACCOUNT_TRADE_LIMITS,
    IST_TIMEZONE,
    NSE_15_SYMBOLS,
    RISK_PER_TRADE_INR,
    settings,
    validate_configuration,
)
from db import DatabaseManager
from news import NewsService
from reminders import ReminderService
from sweep_service import SweepService
from telegram import (
    TelegramConfig,
    TelegramMessage,
    msg_backtest,
    msg_balance,
    msg_error,
    msg_news_pause,
    msg_news_refresh,
    msg_risk,
    msg_scan_result,
    msg_scan_started,
    msg_start,
    msg_stats,
    msg_summary,
    msg_test,
    msg_weekly,
    send_message,
    trade_closed_message,
)
from trading import AccountState
from trendpulse_runtime import TrendPulseRuntime
from trendpulse_service import TrendPulseService
from yahoo_provider import YahooProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("multibot2")

DB = DatabaseManager(settings.db_path)
NEWS = NewsService()
ACCOUNTS: dict[str, AccountState] = {}
ACTIVE: list[dict] = []
HISTORY: list[dict] = []
SIGNALS: list[dict] = []
RUNTIME: TrendPulseRuntime | None = None
TREND: TrendPulseService | None = None
SWEEP: SweepService | None = None
REMINDERS: ReminderService | None = None
STOP = threading.Event()
LOCK = threading.RLock()
NEWS_PAUSE_ENABLED = False
LAST_SCAN: dict = {"status": "NOT_RUN", "at": None, "checked": 0, "directional": 0, "sent": 0}



def now() -> pd.Timestamp:
    return pd.Timestamp.now(tz=IST_TIMEZONE)


def build_market_data_provider() -> YahooProvider:
    validate_runtime_configuration()
    return YahooProvider()


def validate_runtime_configuration() -> None:
    validate_configuration()
    if settings.timezone != IST_TIMEZONE:
        raise ValueError("Locked timezone must be Asia/Kolkata")
    if settings.timeframe != "1h":
        raise ValueError("Locked timeframe must be 1h")
    if settings.market_data_provider != "yahoo":
        raise ValueError("Locked market-data provider must be Yahoo Finance")
    if settings.freshness_hours != 1:
        raise ValueError("Locked signal freshness must be 1 hour")


def init_state() -> None:
    global ACCOUNTS, ACTIVE, HISTORY, SIGNALS
    rows = DB.load_accounts(ACCOUNT_NAMES, ACCOUNT_SIZE_INR, now().date().isoformat())
    ACCOUNTS = {
        name: AccountState(
            name,
            float(rows[name]["starting_balance"]),
            float(rows[name]["balance"]),
            float(rows[name]["planned_risk_used"]),
            int(rows[name]["trades_today"]),
        )
        for name in ACCOUNT_NAMES
    }
    ACTIVE = DB.load_trades("OPEN")
    HISTORY = DB.load_trades("CLOSED")
    SIGNALS = DB.load_signal_history(500)


def ensure_runtime() -> None:
    global RUNTIME, TREND, SWEEP, REMINDERS
    validate_runtime_configuration()
    if not ACCOUNTS:
        init_state()
    if RUNTIME is None:
        RUNTIME = TrendPulseRuntime(provider=build_market_data_provider())
    if TREND is None:
        TREND = TrendPulseService(runtime=RUNTIME, database=DB, accounts=ACCOUNTS)
    if SWEEP is None:
        SWEEP = SweepService(runtime=RUNTIME, database=DB, accounts=ACCOUNTS)
    if REMINDERS is None and settings.telegram_bot_token and settings.telegram_chat_id:
        REMINDERS = ReminderService(DB)


def persist_account(account: AccountState) -> None:
    DB.save_account(
        account.name,
        balance=account.balance,
        trades_today=account.trades_today,
        planned_risk_used=account.planned_risk_used,
        reset_date=now().date().isoformat(),
    )


def trade_row(result) -> dict:
    plan = result.trade.plan
    return {
        "id": f"{result.account}_{result.symbol}_{int(time.time() * 1000)}",
        "status": "OPEN",
        "symbol": result.symbol,
        "account": result.account,
        "strategy": plan.strategy,
        "type": plan.side,
        "entry": plan.entry,
        "sl": plan.stop_loss,
        "tp": plan.take_profit,
        "qty": result.trade.quantity,
        "signal_ts": plan.signal_timestamp.isoformat(),
        "opened_at": now().isoformat(),
    }


def record_result(result) -> None:
    if not result.sent or result.trade is None:
        return
    row = trade_row(result)
    ACTIVE.append(row)
    DB.save_trade(row["id"], "OPEN", row, row["opened_at"])
    persist_account(ACCOUNTS[result.account])


def _record_signal(result) -> None:
    global SIGNALS
    if not result.sent or result.signal.signal not in ("BUY", "SELL"):
        return
    SIGNALS = DB.load_signal_history(500)


def run_trendpulse_cycle(*, now_at=None, send=True, period="30d"):
    global LAST_SCAN
    ensure_runtime()
    results = TREND.scan_universe_and_dispatch(now=now_at, period=period, send=send, account_name="nifty")
    for result in results:
        _record_signal(result)
        record_result(result)
    LAST_SCAN = {
        "status": "COMPLETE",
        "at": now().isoformat(),
        "checked": len(NSE_15_SYMBOLS),
        "directional": sum(r.signal.signal in ("BUY", "SELL") for r in results),
        "sent": sum(bool(r.sent) for r in results),
    }
    return results


def run_sweep_cycle(*, now_at=None, send=True, period="30d"):
    global LAST_SCAN
    ensure_runtime()
    results = SWEEP.scan_universe_and_dispatch(now=now_at, period=period, send=send)
    for result in results:
        _record_signal(result)
        record_result(result)
    LAST_SCAN = {
        "status": "COMPLETE",
        "at": now().isoformat(),
        "checked": len(NSE_15_SYMBOLS),
        "directional": sum(r.signal.signal in ("BUY", "SELL") for r in results),
        "sent": sum(bool(r.sent) for r in results),
    }
    return results


def _price(symbol: str) -> float | None:
    try:
        data = RUNTIME.provider.fetch(f"{symbol}.NS", period="1d", interval="1m", validate_hourly=False)
        return None if data.empty else float(data.close.iloc[-1])
    except Exception:
        return None


def monitor_once() -> None:
    ensure_runtime()
    for row in list(ACTIVE):
        live = _price(row["symbol"])
        if live is None:
            continue
        is_long = row["type"] == "BUY"
        hit_tp = live >= row["tp"] if is_long else live <= row["tp"]
        hit_sl = live <= row["sl"] if is_long else live >= row["sl"]
        if not (hit_tp or hit_sl):
            continue
        pnl = (live - row["entry"]) * row["qty"] if is_long else (row["entry"] - live) * row["qty"]
        row.update(
            status="CLOSED",
            exit_price=live,
            pnl=pnl,
            exit_reason="TP" if hit_tp else "SL",
            closed_at=now().isoformat(),
        )
        ACTIVE.remove(row)
        HISTORY.insert(0, row)
        DB.save_trade(row["id"], "CLOSED", row, row["closed_at"])
        account = ACCOUNTS[row["account"]]
        updated = AccountState(
            account.name,
            account.starting_balance,
            account.balance + pnl,
            max(0.0, account.planned_risk_used - abs(float(row["entry"]) - float(row["sl"])) * float(row["qty"])),
            account.trades_today,
        )
        ACCOUNTS[row["account"]] = updated
        persist_account(updated)
        if settings.telegram_bot_token and settings.telegram_chat_id:
            try:
                send_message(
                    trade_closed_message(row, live, pnl, updated.balance, is_long, hit_tp),
                    TelegramConfig.from_env(),
                )
            except Exception as exc:
                logger.warning("trade-close Telegram send failed: %s", exc)


def scanner_loop() -> None:
    while not STOP.is_set():
        try:
            if now().weekday() < 5 and not NEWS_PAUSE_ENABLED:
                run_trendpulse_cycle(send=True)
                run_sweep_cycle(send=True)
        except Exception:
            logger.exception("scanner cycle failed")
        STOP.wait(settings.scan_interval_seconds)


def monitor_loop() -> None:
    while not STOP.is_set():
        try:
            monitor_once()
        except Exception:
            logger.exception("monitor cycle failed")
        STOP.wait(settings.monitor_interval_seconds)


def _backtest_payload(strategy: str, symbol: str, period: str) -> dict:
    ensure_runtime()
    strategy_key = strategy.strip().lower().replace(" ", "")
    if strategy_key not in {"trendpulse", "sweepv2", "sweep"}:
        raise ValueError("strategy must be TrendPulse or Sweep V2")
    symbol = symbol.strip().upper()
    if symbol not in NSE_15_SYMBOLS:
        raise ValueError("symbol must belong to the locked NSE-15 universe")
    if period not in {"5d", "30d", "60d", "90d", "1y"}:
        raise ValueError("period must be one of 5d, 30d, 60d, 90d or 1y")

    frame = RUNTIME.provider.fetch(f"{symbol}.NS", period=period, interval="1h", validate_hourly=True)
    result = trendpulse_backtest(frame, account="nifty") if strategy_key == "trendpulse" else sweep_backtest(frame, account="sweep_4h")
    daily: dict[str, dict[str, int]] = {}
    rows = []
    for item in result.signals:
        signal = item.signal
        if signal.signal not in ("BUY", "SELL"):
            continue
        day = pd.Timestamp(item.candle_timestamp).tz_convert(IST_TIMEZONE).strftime("%d %b")
        bucket = daily.setdefault(day, {"buy": 0, "sell": 0, "total": 0})
        bucket[signal.signal.lower()] += 1
        bucket["total"] += 1
        rows.append({
            "timestamp": signal.timestamp.isoformat(),
            "direction": signal.signal,
            "reason": signal.reason,
            "entry": signal.entry,
        })
    daily_rows = [{"date": date, **values} for date, values in daily.items()]
    return {
        "strategy": result.strategy,
        "symbol": symbol,
        "period": period,
        "account": result.account,
        "starting_account": result.starting_account,
        "total_signals": result.total_signals,
        "buy_signals": result.buy_signals,
        "sell_signals": result.sell_signals,
        "neutral_signals": result.neutral_signals,
        "trades_taken": result.trades_taken,
        "planned_risk": result.planned_risk,
        "candle_count": len(frame),
        "daily": daily_rows,
        "signals": rows[-200:],
        "generated_at": now().isoformat(),
    }


def snapshot() -> dict:
    ensure_runtime()
    with LOCK:
        account_rows = [
            {
                "name": a.name,
                "starting_balance": a.starting_balance,
                "balance": a.balance,
                "planned_risk_used": a.planned_risk_used,
                "daily_trade_limit": a.daily_trade_limit,
                "max_daily_planned_risk": a.max_daily_planned_risk,
                "trades_today": a.trades_today,
                "remaining_trades": a.remaining_trades,
                "remaining_planned_risk": a.remaining_planned_risk,
            }
            for a in ACCOUNTS.values()
        ]
        news = NEWS.get()
        return {
            "system": {"status": "ONLINE", "mode": "PAPER", "timezone": IST_TIMEZONE, "timeframe": "1h", "leverage": 1},
            "rules": {"account_size_inr": ACCOUNT_SIZE_INR, "risk_per_trade_inr": RISK_PER_TRADE_INR, "account_trade_limits": dict(ACCOUNT_TRADE_LIMITS), "signal_freshness_hours": 1},
            "universe": {"count": 15, "symbols": list(NSE_15_SYMBOLS), "fixed": True},
            "accounts": {"count": 4, "names": list(ACCOUNT_NAMES), "data": account_rows},
            "signals": list(SIGNALS[:500]),
            "trades": ACTIVE + HISTORY[:200],
            "counts": {"signals": len(SIGNALS), "trades": len(ACTIVE) + len(HISTORY), "open_trades": len(ACTIVE), "closed_trades": len(HISTORY)},
            "scan": dict(LAST_SCAN),
            "news": news,
            "generated_at": now().isoformat(),
        }


def _json_response(start, payload, status="200 OK"):
    body = json.dumps(payload, default=str).encode()
    start(status, [("Content-Type", "application/json"), ("Cache-Control", "no-store")])
    return [body]


def web_server() -> None:
    root = os.path.dirname(__file__)
    files = {
        "/": ("dashboard.html", "text/html; charset=utf-8"),
        "/dashboard": ("dashboard.html", "text/html; charset=utf-8"),
        "/app.js": ("app.js", "application/javascript"),
        "/styles.css": ("styles.css", "text/css"),
    }

    def app(env, start):
        path = env.get("PATH_INFO", "/")
        query = parse.parse_qs(env.get("QUERY_STRING", ""))
        if path in ("/ping", "/api/health"):
            payload = {"ok": True, "status": "ONLINE", "timestamp": now().isoformat()}
            if path == "/ping":
                start("200 OK", [("Content-Type", "text/plain"), ("Cache-Control", "no-store")])
                return [b"pong"]
            return _json_response(start, payload)
        if path == "/api/dashboard":
            return _json_response(start, snapshot())
        if path == "/api/news":
            return _json_response(start, NEWS.refresh() if query.get("refresh") == ["1"] else NEWS.get())
        if path == "/api/backtest":
            try:
                strategy = query.get("strategy", ["TrendPulse"])[0]
                symbol = query.get("symbol", [NSE_15_SYMBOLS[0]])[0]
                period = query.get("period", ["30d"])[0]
                return _json_response(start, _backtest_payload(strategy, symbol, period))
            except Exception as exc:
                return _json_response(start, {"ok": False, "error": str(exc)}, "400 Bad Request")
        if path in files:
            name, typ = files[path]
            try:
                with open(os.path.join(root, name), "rb") as handle:
                    body = handle.read()
            except OSError:
                start("404 Not Found", [("Content-Type", "text/plain")])
                return [b"Not found"]
            start("200 OK", [("Content-Type", typ), ("Cache-Control", "no-store")])
            return [body]
        start("404 Not Found", [("Content-Type", "text/plain")])
        return [b"Not found"]

    make_server("0.0.0.0", int(os.getenv("PORT", "10000")), app).serve_forever()


def _send_chat(chat_id: str, message: TelegramMessage | str) -> None:
    config = TelegramConfig.from_env()
    target = TelegramConfig(config.bot_token, str(chat_id))
    if isinstance(message, str):
        message = TelegramMessage("MSG-COMMAND-V1", message)
    send_message(message, target)


def _handle_command(chat_id: str, cmd: str) -> None:
    global NEWS_PAUSE_ENABLED
    try:
        if cmd in ("/start", "/menu"):
            _send_chat(chat_id, msg_start())
        elif cmd in ("/check", "/scan"):
            _send_chat(chat_id, msg_scan_started())
            try:
                trend = run_trendpulse_cycle(send=True)
                sweep = run_sweep_cycle(send=True)
                found = sum(1 for r in trend + sweep if r.sent)
                _send_chat(chat_id, msg_scan_result(found, len(NSE_15_SYMBOLS) * 2))
            except Exception as exc:
                _send_chat(chat_id, msg_error("SCAN", exc))
        elif cmd == "/balance":
            _send_chat(chat_id, msg_balance(ACCOUNTS))
        elif cmd == "/summary":
            _send_chat(chat_id, msg_summary(ACTIVE, HISTORY))
        elif cmd == "/risk":
            _send_chat(chat_id, msg_risk(ACTIVE))
        elif cmd == "/stats":
            _send_chat(chat_id, msg_stats(HISTORY))
        elif cmd == "/weekly":
            _send_chat(chat_id, msg_weekly(HISTORY))
        elif cmd == "/newspause":
            NEWS_PAUSE_ENABLED = not NEWS_PAUSE_ENABLED
            _send_chat(chat_id, msg_news_pause(NEWS_PAUSE_ENABLED))
        elif cmd == "/refreshnews":
            NEWS.refresh()
            _send_chat(chat_id, msg_news_refresh())
        elif cmd == "/backtest":
            _send_chat(chat_id, msg_backtest())
        elif cmd == "/test":
            ensure_runtime()
            test = _price("RELIANCE")
            _send_chat(chat_id, msg_test(test is not None, "RELIANCE.NS price feed responded." if test is not None else "RELIANCE.NS price feed did not respond."))
    except Exception as exc:
        logger.exception("Telegram command failed")
        try:
            _send_chat(chat_id, msg_error(f"COMMAND {cmd}", exc))
        except Exception:
            pass


def telegram_commands() -> None:
    token = settings.telegram_bot_token
    if not token:
        logger.warning("Telegram disabled: TELEGRAM_BOT_TOKEN missing")
        return
    offset = 0
    while not STOP.is_set():
        try:
            payload = parse.urlencode({"timeout": 20, "offset": offset}).encode()
            req = request.Request(f"https://api.telegram.org/bot{token}/getUpdates", data=payload, method="POST")
            with request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read())
            for update in data.get("result", []):
                offset = int(update["update_id"]) + 1
                message = update.get("message", {})
                chat_id = message.get("chat", {}).get("id")
                text = str(message.get("text", ""))
                cmd = text.split()[0].split("@")[0].lower() if text else ""
                if chat_id and cmd:
                    threading.Thread(target=_handle_command, args=(str(chat_id), cmd), daemon=True).start()
        except Exception as exc:
            logger.warning("Telegram polling failed: %s", exc)
            STOP.wait(5)


def main() -> None:
    ensure_runtime()
    threading.Thread(target=web_server, daemon=True, name="dashboard").start()
    threading.Thread(target=scanner_loop, daemon=True, name="scanner").start()
    threading.Thread(target=monitor_loop, daemon=True, name="monitor").start()
    if settings.telegram_bot_token and settings.telegram_chat_id:
        threading.Thread(target=telegram_commands, daemon=True, name="telegram").start()
        if REMINDERS is not None:
            REMINDERS.start()
    logger.info("MULTIBOT2 started: NSE-15, Yahoo, 1H, 1h freshness, paper mode")
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
