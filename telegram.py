"""Telegram output boundary for MULTIBOT2.

Exact historically approved message text is intentionally not fabricated here.
This module provides typed message data and a single rendering boundary so
later approved templates can be added without spreading Telegram formatting
through strategy or trading code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MessageKind = Literal[
    "BUY",
    "SELL",
    "NEUTRAL",
    "STALE",
    "REMINDER",
    "CANDLE_WARNING",
    "DATA_MISMATCH",
]


@dataclass(frozen=True)
class TelegramMessage:
    kind: MessageKind
    text: str


class TelegramTemplateNotConfigured(RuntimeError):
    """Raised when an exact approved Telegram template is not available."""


def render_message(kind: MessageKind, **fields: object) -> TelegramMessage:
    """Render an approved Telegram message.

    Until the exact approved message contract is frozen, failing closed is
    intentional: the bot must never silently invent production message text.
    """
    raise TelegramTemplateNotConfigured(
        f"No approved Telegram template is configured for {kind!r}"
    )
