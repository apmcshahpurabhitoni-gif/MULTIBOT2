"""Complete Telegram message and transport layer for MULTIBOT2.

Every user-facing Telegram message is rendered here so the runtime has one
canonical presentation contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from urllib import parse, request

from strategies import StrategySignal
from trading import PaperTrade

BR = "━━━━━━━━━━━━━━━━━━━━━━"
BR2 = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


class TelegramConfigurationError(RuntimeError):
    pass


class TelegramTemplateError(RuntimeError):
    pass


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    chat_id: str

    @classmethod
    def from_env(cls) -> "TelegramConfig":
        import os
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not token:
            raise TelegramConfigurationError("TELEGRAM_BOT_TOKEN is not configured")
        if not chat_id:
            raise TelegramConfigurationError("TELEGRAM_CHAT_ID is not configured")
        return cls(token, chat_id)


@dataclass(frozen=True)
class TelegramMessage:
    message_type: str
    text: str


APPROVED_TEMPLATES: dict[str, str] = {
    "MSG-SWEEP-BUY-V1": """🟢 *{header_title}* · {status_icon}
{BR}
🪙 *Asset:* `{asset}` (`{symbol}`)
🌐 *Market:* {market}
📊 *Direction:* LONG 📈
⏱ *Timeframe:* {timeframe}
{BR}
⏳ *Signal Status:* `{status_tag}` ({age_str})
⏰ *Candle Closed:* `{time_str}`
{BR}
💼 *PAPER TRADE EXECUTED*
{BR}
🏢 *Account:* `{account}`
📍 *Entry:* `{currency}{entry_fmt}`
🛑 *Stop Loss:* `{currency}{stop_loss_fmt}`
🎯 *Take Profit:* `{currency}{take_profit_fmt}`
📦 *Quantity:* `{quantity_fmt}`
💸 *Risk:* `₹{risk_fmt}`
{BR}
ℹ️ _✅ FRESH = Closed ≤1h ago | ⚠️ STALE = Closed >1h ago_
{BR2}""",
    "MSG-SWEEP-SELL-V1": """🔴 *{header_title}* · {status_icon}
{BR}
🪙 *Asset:* `{asset}` (`{symbol}`)
🌐 *Market:* {market}
📊 *Direction:* SHORT 📉
⏱ *Timeframe:* {timeframe}
{BR}
⏳ *Signal Status:* `{status_tag}` ({age_str})
⏰ *Candle Closed:* `{time_str}`
{BR}
💼 *PAPER TRADE EXECUTED*
{BR}
🏢 *Account:* `{account}`
📍 *Entry:* `{currency}{entry_fmt}`
🛑 *Stop Loss:* `{currency}{stop_loss_fmt}`
🎯 *Take Profit:* `{currency}{take_profit_fmt}`
📦 *Quantity:* `{quantity_fmt}`
💸 *Risk:* `₹{risk_fmt}`
{BR}
ℹ️ _✅ FRESH = Closed ≤1h ago | ⚠️ STALE = Closed >1h ago_
{BR2}""",
    "MSG-TRENDPULSE-BUY-V1": """🟢 *{header_title}* · {status_icon}
{BR}
🪙 *Asset:* `{asset}` (`{symbol}`)
🌐 *Market:* {market}
📊 *Direction:* LONG 📈
⏱ *Timeframe:* {timeframe}
{BR}
⏳ *Signal Status:* `{status_tag}` ({age_str})
⏰ *Candle Closed:* `{time_str}`
{BR}
💼 *PAPER TRADE EXECUTED*
{BR}
🏢 *Account:* `{account}`
📍 *Entry:* `{currency}{entry_fmt}`
🛑 *Stop Loss:* `{currency}{stop_loss_fmt}`
🎯 *Take Profit:* `{currency}{take_profit_fmt}`
📦 *Quantity:* `{quantity_fmt}`
💸 *Risk:* `₹{risk_fmt}`
{BR}
ℹ️ _✅ FRESH = Closed ≤1h ago | ⚠️ STALE = Closed >1h ago_
{BR2}""",
    "MSG-TRENDPULSE-SELL-V1": """🔴 *{header_title}* · {status_icon}
{BR}
🪙 *Asset:* `{asset}` (`{symbol}`)
🌐 *Market:* {market}
📊 *Direction:* SHORT 📉
⏱ *Timeframe:* {timeframe}
{BR}
⏳ *Signal Status:* `{status_tag}` ({age_str})
⏰ *Candle Closed:* `{time_str}`
{BR}
💼 *PAPER TRADE EXECUTED*
{BR}
🏢 *Account:* `{account}`
📍 *Entry:* `{currency}{entry_fmt}`
🛑 *Stop Loss:* `{currency}{stop_loss_fmt}`
🎯 *Take Profit:* `{currency}{take_profit_fmt}`
📦 *Quantity:* `{quantity_fmt}`
💸 *Risk:* `₹{risk_fmt}`
{BR}
ℹ️ _✅ FRESH = Closed ≤1h ago | ⚠️ STALE = Closed >1h ago_
{BR2}""",
}

SWEEP_MESSAGE_TYPES = {"BUY": "MSG-SWEEP-BUY-V1", "SELL": "MSG-SWEEP-SELL-V1"}
TRENDPULSE_MESSAGE_TYPES = {"BUY": "MSG-TRENDPULSE-BUY-V1", "SELL": "MSG-TRENDPULSE-SELL-V1"}


def signal_message_type(signal: StrategySignal) -> str:
    mapping = SWEEP_MESSAGE_TYPES if signal.strategy == "Sweep V2" else TRENDPULSE_MESSAGE_TYPES if signal.strategy == "TrendPulse" else None
    if mapping is None or signal.signal not in mapping:
        raise TelegramTemplateError(f"No approved Telegram template for {signal.strategy}/{signal.signal}")
    return mapping[signal.signal]


def _currency(symbol: str) -> str:
    return "₹" if symbol.endswith(".NS") or "NSE" in symbol or symbol in {"^NSEI", "^NSEBANK"} else "$"


def _display_name(symbol: str, asset: str = "") -> str:
    if asset:
        return asset
    known = {"BTC-USD": "Bitcoin (BTC)", "GC=F": "Gold (XAU/USD)", "SI=F": "Silver (XAG/USD)", "HG=F": "Copper", "^NSEI": "NIFTY 50", "^NSEBANK": "BANK NIFTY"}
    return known.get(symbol, symbol.replace(".NS", ""))


def _price_decimals(symbol: str) -> int:
    if symbol == "BTC-USD": return 2
    if symbol == "USDJPY=X": return 3
    if symbol.endswith("=X"): return 5
    return 2


def build_signal_fields(signal: StrategySignal, *, asset="", symbol="", market="NSE", timeframe="1H", entry=None, stop_loss=None, take_profit=None, quantity=None, risk=None, account="", freshness="FRESH", age_str="") -> dict[str, object]:
    symbol = symbol or ""
    asset = _display_name(symbol, asset)
    decimals = _price_decimals(symbol)
    status_tag = freshness or "FRESH"
    return {
        "BR": BR, "BR2": BR2, "asset": asset, "symbol": symbol, "market": market, "timeframe": timeframe,
        "account": account.upper(), "status_tag": status_tag, "status_icon": "⚠️" if "STALE" in status_tag else "✅",
        "age_str": age_str, "dot": "🟢" if signal.signal == "BUY" else "🔴",
        "header_title": f"{signal.strategy} · {asset}", "time_str": signal.timestamp.strftime("%d-%b-%Y %H:%M IST"),
        "currency": _currency(symbol),
        "entry_fmt": f"{float(entry if entry is not None else signal.entry or 0):,.{decimals}f}",
        "stop_loss_fmt": f"{float(stop_loss or 0):,.{decimals}f}",
        "take_profit_fmt": f"{float(take_profit or 0):,.{decimals}f}",
        "quantity_fmt": f"{float(quantity or 0):.4f}",
        "risk_fmt": f"{float(risk or 0):,.2f}",
    }


def render_template(message_type: str, fields: Mapping[str, object]) -> TelegramMessage:
    template = APPROVED_TEMPLATES.get(message_type)
    if template is None:
        raise TelegramTemplateError(f"Approved Telegram template is not configured: {message_type}")
    try:
        return TelegramMessage(message_type, template.format_map(fields))
    except KeyError as exc:
        raise TelegramTemplateError(f"Template requires unavailable field: {exc.args[0]}") from exc


def render_signal_message(signal: StrategySignal, **fields: object) -> TelegramMessage:
    return render_template(signal_message_type(signal), build_signal_fields(signal, **fields))


def build_trade_fields(trade: PaperTrade) -> dict[str, object]:
    p = trade.plan
    return {"strategy": p.strategy, "side": p.side, "signal_timestamp": p.signal_timestamp.isoformat(), "entry": p.entry, "stop_loss": p.stop_loss, "take_profit": p.take_profit, "risk_per_unit": p.risk_per_unit, "status": trade.status, "exit_price": trade.exit_price if trade.exit_price is not None else "", "exit_timestamp": trade.exit_timestamp.isoformat() if trade.exit_timestamp is not None else "", "exit_reason": trade.exit_reason or ""}


def signal_rejection_message(*, strategy: str, symbol: str, reason: str, detail: str = "") -> TelegramMessage:
    labels = {
        "STALE_SIGNAL": "⏳ Signal is older than the 1-hour freshness limit.",
        "DUPLICATE_SIGNAL_LIMIT": "🔁 This signal has already reached its allowed send limit.",
        "REMINDER_PENDING": "🔔 This signal was already sent and is waiting for its one-hour reminder.",
        "ACCOUNT_DAILY_LIMIT": "🛑 The account has reached its locked daily trade limit.",
        "MISSING_SIGNAL_CANDLE": "🕯️ The required 1H signal candle is unavailable.",
        "INVALID_SWEEP_RISK": "⚠️ Stop-loss distance is invalid, so risk cannot be calculated safely.",
        "NO_DIRECTIONAL_SIGNAL": "💤 The strategy did not produce a BUY or SELL signal.",
    }
    explanation = labels.get(reason, detail or "Signal was not dispatched.")
    extra = f"\n📝 *Detail:* `{detail}`" if detail and detail != explanation else ""
    text = (
        f"⚠️ *SIGNAL NOT SENT*\n{BR}\n"
        f"🧠 *Strategy:* `{strategy}`\n"
        f"🪙 *Asset:* `{symbol}`\n"
        f"🚫 *Reason:* `{reason}`\n"
        f"ℹ️ {explanation}"
        f"{extra}\n{BR}\n"
        f"💼 No paper trade was executed.\n"
        f"{BR2}"
    )
    return TelegramMessage("MSG-SIGNAL-REJECTED-V1", text)


def trade_closed_message(trade: Mapping[str, object], live: float, pnl: float, balance: float, is_long: bool, hit_tp: bool) -> TelegramMessage:
    result = "🎉 WIN" if hit_tp else "💀 LOSS"
    pnl_s = f"+₹{pnl:,.2f}" if pnl >= 0 else f"-₹{abs(pnl):,.2f}"
    symbol = str(trade.get("symbol", "")); name = _display_name(symbol)
    currency = _currency(symbol)
    text = (f"{'🟢' if is_long else '🔴'} *TRADE CLOSED — {result}*\n{BR}\n"
            f"🪙 `{name}` | {'LONG 📈' if is_long else 'SHORT 📉'}\n"
            f"🎯 *Strategy:* {trade.get('strategy', trade.get('strat', 'N/A'))}\n"
            f"🏢 *Account:* `{str(trade.get('account', 'macro')).upper()}`\n{BR}\n"
            f"📍 *Entry:* `{currency}{float(trade.get('entry', 0)):,.2f}`\n"
            f"{'🎯' if hit_tp else '🛑'} *Exit:* `{currency}{live:,.2f}`\n"
            f"🛑 *Stop Loss:* `{currency}{float(trade.get('sl', trade.get('stop_loss', 0))):,.2f}`\n"
            f"🎯 *Take Profit:* `{currency}{float(trade.get('tp', trade.get('take_profit', 0))):,.2f}`\n{BR}\n"
            f"{'💰' if hit_tp else '💸'} *P/L:* `{pnl_s}`\n🏦 *Balance:* `₹{balance:,.2f}`\n{BR2}")
    return TelegramMessage("MSG-TRADE-CLOSED-V1", text)


def msg_start() -> str:
    return (f"🤖 *MAVIS TRADING ENGINE — COMMAND CENTER*\n{BR}\n"
            f"🟢 *SYSTEM:* ONLINE · PAPER MODE\n"
            f"📡 *DATA:* Yahoo Finance · 1H\n"
            f"🇮🇳 *UNIVERSE:* NSE-15\n"
            f"🛡️ *RISK:* ₹2,000 / trade\n{BR}\n"
            f"📊 *OPERATIONAL COMMANDS:*\n"
            f"├ `/start` / `/menu` — Command guide & status\n"
            f"├ `/check` / `/scan` — Force immediate scan\n"
            f"├ `/test` — Test data feeds & latency\n"
            f"├ `/summary` — Open trades & floating P/L\n"
            f"├ `/balance` — View virtual account equity\n"
            f"├ `/stats` — Strategy win-rate & P/L report\n"
            f"├ `/risk` — Portfolio exposure & 1R metrics\n"
            f"├ `/weekly` — 7-day performance digest\n"
            f"├ `/newspause` — Toggle high-impact news pause\n"
            f"├ `/refreshnews` — Refresh news calendar\n"
            f"└ `/backtest` — Run strategy backtester\n{BR2}")


def msg_scan_started() -> str:
    return f"🔍 *SCAN STARTED*\n{BR}\n📡 Checking the locked NSE-15 universe on the 1H timeframe...\n⏳ Please wait for the scan result.\n{BR2}"


def msg_scan_result(found: int, checked: int) -> str:
    return f"🔎 *SCAN COMPLETE*\n{BR}\n📊 Checked: `{checked}` assets\n🎯 New signals: `{found}`\n{'🟢 Signals dispatched to Telegram.' if found else '💤 No fresh approved signals found.'}\n{BR2}"


def msg_balance(accounts: Mapping[str, object]) -> str:
    lines = [f"💰 *VIRTUAL ACCOUNT BALANCE*", BR]
    for name, a in accounts.items():
        lines.append(f"{('🌐' if name=='macro' else '🇮🇳' if name=='nifty' else '🇺🇸' if name=='ny_session' else '🔵')} *{name.replace('_',' ').title()}:* `₹{float(a.balance):,.2f}` · `{int(a.trades_today)}/{int(a.daily_trade_limit)}`")
    lines.append(BR2); return "\n".join(lines)


def msg_summary(active: list[Mapping[str, object]], history: list[Mapping[str, object]]) -> str:
    floating = 0.0
    for t in active:
        floating += 0.0
    return f"📋 *PORTFOLIO SUMMARY*\n{BR}\n🟡 *Open Trades:* `{len(active)}`\n📚 *Closed Trades:* `{len(history)}`\n💹 *Floating P/L:* `₹{floating:,.2f}`\n{BR2}"


def msg_risk(active: list[Mapping[str, object]]) -> str:
    risk = sum(abs(float(t.get("entry",0))-float(t.get("sl",0)))*float(t.get("qty",0)) for t in active)
    return f"🛡️ *PORTFOLIO RISK*\n{BR}\n🔥 *Open Planned Risk:* `₹{risk:,.2f}`\n📌 *Per-trade risk cap:* `₹2,000.00`\n⚙️ *Leverage:* `1x`\n{BR2}"


def msg_stats(history: list[Mapping[str, object]]) -> str:
    wins = sum(1 for t in history if str(t.get("exit_reason", "")).upper() == "TP" or float(t.get("pnl",0)) > 0)
    losses = sum(1 for t in history if float(t.get("pnl",0)) < 0)
    pnl = sum(float(t.get("pnl",0)) for t in history)
    total = wins + losses
    wr = wins / total * 100 if total else 0.0
    return f"📊 *PERFORMANCE STATS*\n{BR}\n📈 *Trades:* `{len(history)}`\n✅ *Wins:* `{wins}`\n❌ *Losses:* `{losses}`\n🎯 *Win Rate:* `{wr:.1f}%`\n💰 *Total P/L:* `{'+' if pnl>=0 else ''}₹{pnl:,.2f}`\n{BR2}"


def msg_weekly(history: list[Mapping[str, object]]) -> str:
    pnl = sum(float(t.get("pnl",0)) for t in history[-7:]); wins = sum(1 for t in history[-7:] if float(t.get("pnl",0))>0); losses = sum(1 for t in history[-7:] if float(t.get("pnl",0))<0)
    total = wins + losses; wr = wins/total*100 if total else 0
    return f"🗓️ *WEEKLY DIGEST*\n{BR}\n📈 *7-Day P/L:* `{'+' if pnl>=0 else ''}₹{pnl:,.2f}`\n📊 *Trades:* `{total}` · ✅ `{wins}W` · ❌ `{losses}L` · 🎯 `{wr:.1f}%`\n{BR2}"


def msg_test(ok: bool, detail: str) -> str:
    return f"🧪 *DATA FEED TEST*\n{BR}\n{'🟢' if ok else '🔴'} *Status:* `{'ONLINE' if ok else 'FAILED'}`\n📡 *Yahoo Finance:* {detail}\n⏱️ *Runtime:* 1H\n{BR2}"


def msg_news_pause(enabled: bool) -> str:
    return f"📰 *NEWS PAUSE*\n{BR}\n{'🟡 ENABLED' if enabled else '🟢 DISABLED'}\n{'⏸️ New signal dispatch is paused.' if enabled else '▶️ Normal signal dispatch resumed.'}\n{BR2}"


def msg_news_refresh() -> str:
    return f"📰 *NEWS CALENDAR REFRESH*\n{BR}\n🔄 Refresh requested.\n📡 Runtime will use the configured news source when available.\n{BR2}"


def msg_backtest() -> str:
    return f"📈 *BACKTEST ENGINE*\n{BR}\n🧪 Backtest request received.\n⚙️ Strategy rules remain locked to MULTIBOT2.\n💼 Results are analytical only — no live orders.\n{BR2}"


def msg_error(context: str, error: object) -> str:
    return f"⚠️ *ERROR — {context}*\n{BR}\n❌ `{str(error)[:700]}`\n🛡️ Paper mode remains active.\n{BR2}"


def reminder_message(original_text: str) -> TelegramMessage:
    return TelegramMessage("MSG-REMINDER-V1", f"🔔 *SIGNAL REMINDER*\n{BR}\n{original_text}\n{BR2}")


def send_message(message: TelegramMessage, config: TelegramConfig) -> None:
    if not message.text.strip():
        raise TelegramTemplateError("Cannot send an empty Telegram message")
    endpoint = f"https://api.telegram.org/bot{config.bot_token}/sendMessage"
    payload = parse.urlencode({"chat_id": config.chat_id, "text": message.text, "parse_mode": "Markdown"}).encode()
    req = request.Request(endpoint, data=payload, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
    with request.urlopen(req, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f"Telegram API request failed: HTTP {response.status}")


__all__ = [
    "TelegramConfig", "TelegramMessage", "TelegramConfigurationError", "TelegramTemplateError",
    "APPROVED_TEMPLATES", "signal_message_type", "render_signal_message", "send_message",
    "signal_rejection_message", "trade_closed_message", "msg_start", "msg_scan_started", "msg_scan_result",
    "msg_balance", "msg_summary", "msg_risk", "msg_stats", "msg_weekly", "msg_test", "msg_news_pause",
    "msg_news_refresh", "msg_backtest", "msg_error", "reminder_message", "build_trade_fields",
]
