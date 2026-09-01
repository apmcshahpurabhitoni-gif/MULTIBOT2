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

        return cls(
            bot_token=token,
            chat_id=chat_id,
        )


@dataclass(frozen=True)
class TelegramMessage:
    """A rendered Telegram message."""

    message_type: str
    text: str


# ============================================================
# APPROVED MESSAGE REGISTRY
#
# DO NOT INVENT MESSAGE TEXT HERE.
#
# Exact approved wording, emojis and formatting will be inserted
# only after recovery from the approved source.
# ============================================================

APPROVED_TEMPLATES: dict[str, str] = {}


# ============================================================
# MESSAGE IDENTIFIERS
# ============================================================

SWEEP_MESSAGE_TYPES = {
    "BUY": "MSG-SWEEP-BUY-V1",
    "SELL": "MSG-SWEEP-SELL-V1",
    "NEUTRAL": "MSG-SWEEP-NEUTRAL-V1",
}

TRENDPULSE_MESSAGE_TYPES = {
    "BUY": "MSG-TRENDPULSE-BUY-V1",
    "SELL": "MSG-TRENDPULSE-SELL-V1",
    "NEUTRAL": "MSG-TRENDPULSE-NEUTRAL-V1",
}


def signal_message_type(
    signal: StrategySignal,
) -> str:
    """Return the approved template identifier."""

    if signal.strategy == "Sweep V2":

        mapping = SWEEP_MESSAGE_TYPES

    elif signal.strategy == "TrendPulse":

        mapping = TRENDPULSE_MESSAGE_TYPES

    else:

        raise TelegramTemplateError(
            f"Unsupported strategy: {signal.strategy}"
        )

    if signal.signal not in mapping:

        raise TelegramTemplateError(
            f"Signal has no standard message template: "
            f"{signal.signal}"
        )

    return mapping[signal.signal]


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
    freshness: str = "",
) -> dict[str, object]:
    """Build the canonical fields available to templates."""

    return {
        "strategy": signal.strategy,
        "signal": signal.signal,
        "timestamp": signal.timestamp.isoformat(),
        "reason": signal.reason,
        "asset": asset,
        "symbol": symbol,
        "market": market,
        "timeframe": timeframe,
        "entry": (
            entry
            if entry is not None
            else ""
        ),
        "stop_loss": (
            stop_loss
            if stop_loss is not None
            else ""
        ),
        "take_profit": (
            take_profit
            if take_profit is not None
            else ""
        ),
        "freshness": freshness,
    }


def render_template(
    message_type: str,
    fields: Mapping[str, object],
) -> TelegramMessage:
    """Render an approved template.

    Fails closed if the approved wording is unavailable.
    """

    template = APPROVED_TEMPLATES.get(
        message_type
    )

    if template is None:

        raise TelegramTemplateError(
            "Approved Telegram template is not "
            f"configured: {message_type}"
        )

    try:

        text = template.format_map(
            fields
        )

    except KeyError as exc:

        raise TelegramTemplateError(
            "Template requires unavailable field: "
            f"{exc.args[0]}"
        ) from exc

    return TelegramMessage(
        message_type=message_type,
        text=text,
    )


def render_signal_message(
    signal: StrategySignal,
    **fields: object,
) -> TelegramMessage:
    """Render a strategy signal using an approved template."""

    message_type = signal_message_type(
        signal
    )

    signal_fields = build_signal_fields(
        signal,
        **fields,
    )

    return render_template(
        message_type,
        signal_fields,
    )


def build_trade_fields(
    trade: PaperTrade,
) -> dict[str, object]:
    """Return canonical trade fields."""

    plan = trade.plan

    return {
        "strategy": plan.strategy,
        "side": plan.side,
        "signal_timestamp": (
            plan.signal_timestamp.isoformat()
        ),
        "entry": plan.entry,
        "stop_loss": plan.stop_loss,
        "take_profit": plan.take_profit,
        "risk_per_unit": plan.risk_per_unit,
        "status": trade.status,
        "exit_price": (
            trade.exit_price
            if trade.exit_price is not None
            else ""
        ),
        "exit_timestamp": (
            trade.exit_timestamp.isoformat()
            if trade.exit_timestamp is not None
            else ""
        ),
        "exit_reason": (
            trade.exit_reason
            or ""
        ),
    }


def send_message(
    message: TelegramMessage,
    config: TelegramConfig,
) -> None:
    """Send one Telegram message using the Bot API."""

    if not message.text.strip():

        raise TelegramTemplateError(
            "Cannot send an empty Telegram message"
        )

    endpoint = (
        "https://api.telegram.org/bot"
        f"{config.bot_token}/sendMessage"
    )

    payload = parse.urlencode(
        {
            "chat_id": config.chat_id,
            "text": message.text,
        }
    ).encode("utf-8")

    http_request = request.Request(
        endpoint,
        data=payload,
        method="POST",
        headers={
            "Content-Type":
                "application/x-www-form-urlencoded",
        },
    )

    with request.urlopen(
        http_request,
        timeout=15,
    ) as response:

        if response.status != 200:

            raise RuntimeError(
                "Telegram API request failed: "
                f"HTTP {response.status}"
            )
