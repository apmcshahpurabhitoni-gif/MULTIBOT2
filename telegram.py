"""Telegram message and delivery boundary for MULTIBOT2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from strategies import StrategySignal
from trading import PaperTrade


class TelegramConfigurationError(RuntimeError):
    """Raised when Telegram configuration is incomplete."""


class TelegramTemplateError(RuntimeError):
    """Raised when an approved message template is unavailable."""


@dataclass(frozen=True)
class TelegramConfig:
    """Telegram connection configuration."""

    bot_token: str
    chat_id: str

    def __post_init__(self) -> None:
        if not self.bot_token.strip():
            raise TelegramConfigurationError(
                "Telegram bot token cannot be empty"
            )

        if not self.chat_id.strip():
            raise TelegramConfigurationError(
                "Telegram chat ID cannot be empty"
            )


@dataclass(frozen=True)
class TelegramMessage:
    """A rendered Telegram message."""

    message_type: str
    text: str


# The exact approved production templates must be inserted here
# only after they have been verified from the approved source.
APPROVED_TEMPLATES: dict[str, str] = {}


def build_fields(
    signal: StrategySignal,
    *,
    asset: str | None = None,
    symbol: str | None = None,
    market: str | None = None,
    timeframe: str | None = None,
    entry: float | None = None,
    stop_loss: float | None = None,
    take_profit: float | None = None,
    freshness: str | None = None,
) -> dict[str, object]:
    """Build the canonical fields available to Telegram templates."""

    return {
        "strategy": signal.strategy,
        "signal": signal.signal,
        "timestamp": signal.timestamp.isoformat(),
        "reason": signal.reason,
        "asset": asset or "",
        "symbol": symbol or "",
        "market": market or "",
        "timeframe": timeframe or "",
        "entry": entry if entry is not None else "",
        "stop_loss": stop_loss if stop_loss is not None else "",
        "take_profit": take_profit if take_profit is not None else "",
        "freshness": freshness or "",
    }


def render_template(
    message_type: str,
    fields: Mapping[str, object],
) -> TelegramMessage:
    """Render an approved template.

    Fails closed when no approved template exists. This prevents the bot
    from silently sending fabricated Telegram wording.
    """

    template = APPROVED_TEMPLATES.get(message_type)

    if template is None:
        raise TelegramTemplateError(
            f"No approved Telegram template configured: {message_type}"
        )

    try:
        text = template.format_map(fields)
    except KeyError as exc:
        raise TelegramTemplateError(
            f"Missing Telegram template field: {exc.args[0]}"
        ) from exc

    return TelegramMessage(
        message_type=message_type,
        text=text,
    )


def signal_message_type(signal: StrategySignal) -> str:
    """Map a signal to its template identifier."""

    mapping = {
        "BUY": "MSG-TRENDPULSE-BUY-V1",
        "SELL": "MSG-TRENDPULSE-SELL-V1",
        "NEUTRAL": "MSG-TRENDPULSE-NEUTRAL-V1",
        "NO_SIGNAL": "MSG-TRENDPULSE-NEUTRAL-V1",
    }

    if signal.strategy == "Sweep V2":
        mapping = {
            "BUY": "MSG-SWEEP-BUY-V1",
            "SELL": "MSG-SWEEP-SELL-V1",
            "NEUTRAL": "MSG-SWEEP-NEUTRAL-V1",
            "NO_SIGNAL": "MSG-SWEEP-NEUTRAL-V1",
        }

    try:
        return mapping[signal.signal]
    except KeyError as exc:
        raise TelegramTemplateError(
            f"Unsupported signal type: {signal.signal}"
        ) from exc


def render_signal_message(
    signal: StrategySignal,
    **fields: object,
) -> TelegramMessage:
    """Render the correct approved message for a strategy signal."""

    message_type = signal_message_type(signal)

    template_fields = build_fields(
        signal,
        **fields,
    )

    return render_template(
        message_type,
        template_fields,
    )


def trade_fields(trade: PaperTrade) -> dict[str, object]:
    """Return canonical trade fields for an approved template."""

    plan = trade.plan

    return {
        "strategy": plan.strategy,
        "side": plan.side,
        "signal_timestamp": plan.signal_timestamp.isoformat(),
        "entry": plan.entry,
        "stop_loss": plan.stop_loss,
        "take_profit": plan.take_profit,
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
        "exit_reason": trade.exit_reason or "",
    }
