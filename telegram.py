"""Canonical Telegram formatting boundary for MULTIBOT2.

Formatting is kept separate from strategy and trading calculations. The trade
signal and trade-closed formats below are ported from the reviewed legacy
message builders; unresolved message types remain fail-closed until their
exact approved wording is confirmed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

MessageKind = Literal[
    "BUY",
    "SELL",
    "NEUTRAL",
    "STALE",
    "REMINDER",
    "CANDLE_WARNING",
    "DATA_MISMATCH",
    "TRADE_CLOSED",
]

BR = "━━━━━━━━━━━━━━━━━━━━━━"
BR2 = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
IST = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True)
class TelegramMessage:
    kind: MessageKind
    text: str


class TelegramTemplateNotConfigured(RuntimeError):
    """Raised when an exact approved Telegram template is unavailable."""


def display_name(symbol: str) -> str:
    """Return the established user-facing name for a provider symbol."""
    names = {
        "BTC-USD": "Bitcoin (BTC)",
        "GC=F": "Gold (XAU/USD)",
        "SI=F": "Silver (XAG/USD)",
        "HG=F": "Copper",
        "EURUSD=X": "EUR/USD",
        "GBPUSD=X": "GBP/USD",
        "USDJPY=X": "USD/JPY",
        "USDCHF=X": "USD/CHF",
        "AUDUSD=X": "AUD/USD",
        "USDCAD=X": "USD/CAD",
        "NZDUSD=X": "NZD/USD",
        "^NSEI": "NIFTY 50",
        "^NSEBANK": "BANK NIFTY",
    }
    if symbol in names:
        return names[symbol]
    return symbol.replace("=X", "").replace(".NS", "").replace("^", "")


def _age_text(signal_ts_ms: int, now: datetime | None = None) -> tuple[str, str]:
    """Render the canonical one-hour freshness state."""
    now = now or datetime.now(IST)
    signal_dt = datetime.fromtimestamp(signal_ts_ms / 1000, tz=IST)
    age_seconds = (now - signal_dt).total_seconds()
    if age_seconds < 0:
        raise ValueError("Signal timestamp cannot be in the future")
    minutes = int(age_seconds // 60)
    if age_seconds <= 3600:
        tag = "✅ FRESH"
    else:
        tag = "⚠️ STALE"
    if minutes < 60:
        age = f"{minutes} min ago"
    else:
        age = f"{minutes // 60} hr {minutes % 60} min ago"
    return age, tag


def render_trade_signal(
    symbol: str,
    market: str,
    strategy: str,
    signal: Literal["BUY", "SELL"],
    timeframe: str,
    price: float,
    stop_loss: float,
    take_profit: float,
    quantity: float,
    risk_amount: float,
    account: str,
    signal_ts_ms: int,
    *,
    currency: str = "₹",
    now: datetime | None = None,
) -> TelegramMessage:
    """Render the reviewed paper-trade Telegram format."""
    if signal not in {"BUY", "SELL"}:
        raise ValueError("Trade message requires BUY or SELL")
    age, tag = _age_text(signal_ts_ms, now)
    signal_dt = datetime.fromtimestamp(signal_ts_ms / 1000, tz=IST)
    dot = "🟢" if signal == "BUY" else "🔴"
    direction = "LONG 📈" if signal == "BUY" else "SHORT 📉"
    status_icon = "✅" if tag == "✅ FRESH" else "⚠️"
    name = display_name(symbol)
    text = (
        f"{dot} *{strategy} · {name}* · {status_icon}\n{BR}\n"
        f"🪙 *Asset:* `{name}` (`{symbol}`)\n"
        f"🌐 *Market:* {market}\n"
        f"📊 *Direction:* {direction}\n"
        f"⏱ *Timeframe:* {timeframe}\n{BR}\n"
        f"⏳ *Signal Status:* `{tag}` ({age})\n"
        f"⏰ *Candle Closed:* `{signal_dt.strftime('%d-%b-%Y %H:%M IST')}`\n{BR}\n"
        f"💼 *PAPER TRADE EXECUTED*\n{BR}\n"
        f"🏢 *Account:* `{account.upper()}`\n"
        f"📍 *Entry:* `{currency}{price:,.4f}`\n"
        f"🛑 *Stop Loss:* `{currency}{stop_loss:,.4f}`\n"
        f"🎯 *Take Profit:* `{currency}{take_profit:,.4f}`\n"
        f"📦 *Quantity:* `{quantity:.4f}`\n"
        f"💸 *Risk:* `₹{risk_amount:,.2f}`\n{BR}\n"
        f"ℹ️ _✅ FRESH = Closed ≤1h ago | ⚠️ STALE = Closed >1h ago_\n{BR2}"
    )
    return TelegramMessage("BUY" if signal == "BUY" else "SELL", text)


def render_trade_closed(
    trade: dict,
    exit_price: float,
    pnl: float,
    balance: float,
    *,
    is_long: bool,
    hit_tp: bool,
    currency: str = "₹",
) -> TelegramMessage:
    """Render the reviewed trade-closed message."""
    result = "🎉 WIN" if hit_tp else "💀 LOSS"
    dot = "🟢" if is_long else "🔴"
    money = "💰" if hit_tp else "💸"
    pnl_text = f"+₹{pnl:,.2f}" if hit_tp else f"-₹{abs(pnl):,.2f}"
    symbol = trade["symbol"]
    name = display_name(symbol)
    direction = "LONG" if is_long else "SHORT"
    text = (
        f"{dot} *TRADE CLOSED — {result}*\n{BR}\n"
        f"🪙 `{name}` | {direction}\n"
        f"🎯 *Strategy:* {trade.get('strat', 'N/A')}\n"
        f"🏢 *Account:* `{trade.get('account', 'MACRO').upper()}`\n{BR}\n"
        f"📍 *Entry:* `{currency}{trade['entry']:,.4f}`\n"
        f"{'📈' if hit_tp else '📉'} *Exit:* `{currency}{exit_price:,.4f}`\n"
        f"🛑 *SL Hit:* `{currency}{trade['trail_sl']:,.4f}`\n"
        f"🎯 *TP Target:* `{currency}{trade['tp']:,.4f}`\n{BR}\n"
        f"{money} *P/L:* `{pnl_text}`\n"
        f"🏦 *Balance:* `₹{balance:,.2f}`\n{BR2}"
    )
    return TelegramMessage("TRADE_CLOSED", text)


def render_message(kind: MessageKind, **fields: object) -> TelegramMessage:
    """Render only message formats whose exact contract is established."""
    if kind in {"BUY", "SELL"}:
        return render_trade_signal(**fields)  # type: ignore[arg-type]
    if kind == "TRADE_CLOSED":
        return render_trade_closed(**fields)  # type: ignore[arg-type]
    raise TelegramTemplateNotConfigured(
        f"No approved Telegram template is configured for {kind!r}"
    )
