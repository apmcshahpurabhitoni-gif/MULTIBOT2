"""Telegram integration boundary for MULTIBOT2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from urllib import parse, request

from strategies import StrategySignal
from trading import PaperTrade


class TelegramConfigurationError(RuntimeError):
    """Raised when Telegram configuration is missing."""


class TelegramTemplateError(RuntimeError):
    """Raised when an approved Telegram template is unavailable."""


@dataclass(frozen=True)
class TelegramConfig:
    """Telegram connection configuration."""

    bot_token: str
    chat_id: str

    @classmethod
    def from_env(cls) -> "TelegramConfig":
        import os

        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if not token:
            raise TelegramConfigurationError(
                "TELEGRAM_BOT_TOKEN is not configured"
            )

        if not chat_id:
            raise TelegramConfigurationError(
                "TELEGRAM_CHAT_ID is not configured"
            )

        return cls(bot_token=token, chat_id=chat_id)


@dataclass(frozen=True)
class TelegramMessage:
    """A rendered Telegram message."""

    message_type: str
    text: str


BR = "━━━━━━━━━━━━━━━━━━━━━━"
BR2 = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Exact approved trade-signal contract recovered from the approved source.
# Keep wording, order, emojis and separators unchanged.
APPROVED_TEMPLATES: dict[str, str] = {
    "MSG-SWEEP-BUY-V1": (
        "{dot} *{header_title}* · {status_icon}\n{BR}\n"
        "🪙 *Asset:* `{asset}` (`{symbol}`)\n"
        "🌐 *Market:* {market}\n"
        "📊 *Direction:* LONG 📈\n"
        "⏱ *Timeframe:* {timeframe}\n{BR}\n"
        "⏳ *Signal Status:* `{status_tag}` ({age_str})\n"
        "⏰ *Candle Closed:* `{time_str}`\n{BR}\n"
        "💼 *PAPER TRADE EXECUTED*\n{BR}\n"
        "🏢 *Account:* `{account}`\n"
        "📍 *Entry:* `{currency}{entry_fmt}`\n"
        "🛑 *Stop Loss:* `{currency}{stop_loss_fmt}`\n"
        "🎯 *Take Profit:* `{currency}{take_profit_fmt}`\n"
        "📦 *Quantity:* `{quantity_fmt}`\n"
        "💸 *Risk:* `₹{risk_fmt}`\n{BR}\n"
        "ℹ️ _✅ FRESH = Closed ≤1h ago | ⚠️ STALE = Closed >1h ago_\n"
        "{BR2}"
    ),
    "MSG-SWEEP-SELL-V1": (
        "{dot} *{header_title}* · {status_icon}\n{BR}\n"
        "🪙 *Asset:* `{asset}` (`{symbol}`)\n"
        "🌐 *Market:* {market}\n"
        "📊 *Direction:* SHORT 📉\n"
        "⏱ *Timeframe:* {timeframe}\n{BR}\n"
        "⏳ *Signal Status:* `{status_tag}` ({age_str})\n"
        "⏰ *Candle Closed:* `{time_str}`\n{BR}\n"
        "💼 *PAPER TRADE EXECUTED*\n{BR}\n"
        "🏢 *Account:* `{account}`\n"
        "📍 *Entry:* `{currency}{entry_fmt}`\n"
        "🛑 *Stop Loss:* `{currency}{stop_loss_fmt}`\n"
        "🎯 *Take Profit:* `{currency}{take_profit_fmt}`\n"
        "📦 *Quantity:* `{quantity_fmt}`\n"
        "💸 *Risk:* `₹{risk_fmt}`\n{BR}\n"
        "ℹ️ _✅ FRESH = Closed ≤1h ago | ⚠️ STALE = Closed >1h ago_\n"
        "{BR2}"
    ),
    "MSG-TRENDPULSE-BUY-V1": (
        "{dot} *{header_title}* · {status_icon}\n{BR}\n"
        "🪙 *Asset:* `{asset}` (`{symbol}`)\n"
        "🌐 *Market:* {market}\n"
        "📊 *Direction:* LONG 📈\n"
        "⏱ *Timeframe:* {timeframe}\n{BR}\n"
        "⏳ *Signal Status:* `{status_tag}` ({age_str})\n"
        "⏰ *Candle Closed:* `{time_str}`\n{BR}\n"
        "💼 *PAPER TRADE EXECUTED*\n{BR}\n"
        "🏢 *Account:* `{account}`\n"
        "📍 *Entry:* `{currency}{entry_fmt}`\n"
        "🛑 *Stop Loss:* `{currency}{stop_loss_fmt}`\n"
        "🎯 *Take Profit:* `{currency}{take_profit_fmt}`\n"
        "📦 *Quantity:* `{quantity_fmt}`\n"
        "💸 *Risk:* `₹{risk_fmt}`\n{BR}\n"
        "ℹ️ _✅ FRESH = Closed ≤1h ago | ⚠️ STALE = Closed >1h ago_\n"
        "{BR2}"
    ),
    "MSG-TRENDPULSE-SELL-V1": (
        "{dot} *{header_title}* · {status_icon}\n{BR}\n"
        "🪙 *Asset:* `{asset}` (`{symbol}`)\n"
        "🌐 *Market:* {market}\n"
        "📊 *Direction:* SHORT 📉\n"
        "⏱ *Timeframe:* {timeframe}\n{BR}\n"
        "⏳ *Signal Status:* `{status_tag}` ({age_str})\n"
        "⏰ *Candle Closed:* `{time_str}`\n{BR}\n"
        "💼 *PAPER TRADE EXECUTED*\n{BR}\n"
        "🏢 *Account:* `{account}`\n"
        "📍 *Entry:* `{currency}{entry_fmt}`\n"
        "🛑 *Stop Loss:* `{currency}{stop_loss_fmt}`\n"
        "🎯 *Take Profit:* `{currency}{take_profit_fmt}`\n"
        "📦 *Quantity:* `{quantity_fmt}`\n"
        "💸 *Risk:* `₹{risk_fmt}`\n{BR}\n"
        "ℹ️ _✅ FRESH = Closed ≤1h ago | ⚠️ STALE = Closed >1h ago_\n"
        "{BR2}"
    ),
}

SWEEP_MESSAGE_TYPES = {
    "BUY": "MSG-SWEEP-BUY-V1",
    "SELL": "MSG-SWEEP-SELL-V1",
}

TRENDPULSE_MESSAGE_TYPES = {
    "BUY": "MSG-TRENDPULSE-BUY-V1",
    "SELL": "MSG-TRENDPULSE-SELL-V1",
}


def signal_message_type(signal: StrategySignal) -> str:
    """Return the approved template identifier."""
    if signal.strategy == "Sweep V2":
        mapping = SWEEP_MESSAGE_TYPES
    elif signal.strategy == "TrendPulse":
        mapping = TRENDPULSE_MESSAGE_TYPES
    else:
        raise TelegramTemplateError(f"Unsupported strategy: {signal.strategy}")

    if signal.signal not in mapping:
        raise TelegramTemplateError(
            f"Signal has no standard message template: {signal.signal}"
        )
    return mapping[signal.signal]


def _price_decimals(symbol: str) -> int:
    if symbol == "BTC-USD":
        return 2
    if symbol == "USDJPY=X":
        return 3
    if symbol.endswith("=X"):
        return 5
    if symbol in {"GC=F", "SI=F", "HG=F"}:
        return 2
    return 2


def _currency(symbol: str) -> str:
    return "₹" if symbol.endswith(".NS") or "NSE" in symbol or symbol in {"^NSEI", "^NSEBANK"} else "$"


def _display_name(symbol: str, asset: str) -> str:
    if asset:
        return asset
    known = {
        "BTC-USD": "Bitcoin (BTC)",
        "GC=F": "Gold (XAU/USD)",
        "^NSEI": "NIFTY 50",
        "^NSEBANK": "BANK NIFTY",
    }
    return known.get(symbol, symbol.replace(".NS", ""))


def build_signal_fields(
    signal: StrategySignal,
    *,
    asset: str = "",
    symbol: str = "",
    market: str = "NSE",
    timeframe: str = "1H",
    entry: float | None = None,
    stop_loss: float | None = None,
    take_profit: float | None = None,
    quantity: float | None = None,
    risk: float | None = None,
    account: str = "",
    freshness: str = "",
    age_str: str = "",
) -> dict[str, object]:
    """Build canonical fields for the approved trade-signal contract."""
    symbol = symbol or ""
    asset = _display_name(symbol, asset)
    currency = _currency(symbol)
    status_tag = freshness or "FRESH"
    status_icon = "⚠️" if "STALE" in status_tag else "✅"
    dot = "🟢" if signal.signal == "BUY" else "🔴"
    entry_value = float(entry if entry is not None else signal.entry or 0)
    sl_value = float(stop_loss if stop_loss is not None else 0)
    tp_value = float(take_profit if take_profit is not None else 0)
    qty_value = float(quantity if quantity is not None else 0)
    risk_value = float(risk if risk is not None else 0)
    decimals = _price_decimals(symbol)

    return {
        "BR": BR,
        "BR2": BR2,
        "strategy": signal.strategy,
        "signal": signal.signal,
        "timestamp": signal.timestamp.isoformat(),
        "reason": signal.reason,
        "asset": asset,
        "symbol": symbol,
        "market": market,
        "timeframe": timeframe,
        "entry": entry_value,
        "stop_loss": sl_value,
        "take_profit": tp_value,
        "quantity": qty_value,
        "risk": risk_value,
        "account": account.upper(),
        "freshness": freshness,
        "age_str": age_str,
        "status_tag": status_tag,
        "status_icon": status_icon,
        "dot": dot,
        "header_title": f"{signal.strategy} · {asset}",
        "time_str": signal.timestamp.strftime("%d-%b-%Y %H:%M IST"),
        "currency": currency,
        "entry_fmt": f"{entry_value:,.{decimals}f}",
        "stop_loss_fmt": f"{sl_value:,.{decimals}f}",
        "take_profit_fmt": f"{tp_value:,.{decimals}f}",
        "quantity_fmt": f"{qty_value:.4f}",
        "risk_fmt": f"{risk_value:,.2f}",
    }


def render_template(message_type: str, fields: Mapping[str, object]) -> TelegramMessage:
    """Render an approved template; fail closed when unavailable."""
    template = APPROVED_TEMPLATES.get(message_type)
    if template is None:
        raise TelegramTemplateError(
            "Approved Telegram template is not configured: " + message_type
        )
    try:
        text = template.format_map(fields)
    except KeyError as exc:
        raise TelegramTemplateError(
            "Template requires unavailable field: " + str(exc.args[0])
        ) from exc
    return TelegramMessage(message_type=message_type, text=text)


def render_signal_message(signal: StrategySignal, **fields: object) -> TelegramMessage:
    """Render a strategy signal using an approved template."""
    message_type = signal_message_type(signal)
    return render_template(message_type, build_signal_fields(signal, **fields))


def build_trade_fields(trade: PaperTrade) -> dict[str, object]:
    """Return canonical trade fields."""
    plan = trade.plan
    return {
        "strategy": plan.strategy,
        "side": plan.side,
        "signal_timestamp": plan.signal_timestamp.isoformat(),
        "entry": plan.entry,
        "stop_loss": plan.stop_loss,
        "take_profit": plan.take_profit,
        "risk_per_unit": plan.risk_per_unit,
        "status": trade.status,
        "exit_price": trade.exit_price if trade.exit_price is not None else "",
        "exit_timestamp": trade.exit_timestamp.isoformat() if trade.exit_timestamp is not None else "",
        "exit_reason": trade.exit_reason or "",
    }


def send_message(message: TelegramMessage, config: TelegramConfig) -> None:
    """Send one approved Telegram message using Markdown formatting."""
    if not message.text.strip():
        raise TelegramTemplateError("Cannot send an empty Telegram message")

    endpoint = f"https://api.telegram.org/bot{config.bot_token}/sendMessage"
    payload = parse.urlencode(
        {
            "chat_id": config.chat_id,
            "text": message.text,
            "parse_mode": "Markdown",
        }
    ).encode("utf-8")
    http_request = request.Request(
        endpoint,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with request.urlopen(http_request, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(
                f"Telegram API request failed: HTTP {response.status}"
            )
