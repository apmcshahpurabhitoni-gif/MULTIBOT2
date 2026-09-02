"""MULTIBOT2 startup announcement.

This is a complete, standalone startup notifier. Render runs it immediately
before main.py so every process start announces exactly what build is running.
It only uses Telegram sendMessage; it does not start polling and therefore
cannot create a Telegram getUpdates conflict.
"""
from __future__ import annotations

import json
import logging
import os
from urllib import parse, request

APP_NAME = "MULTIBOT2"
APP_VERSION = os.getenv("MULTIBOT2_VERSION", "1.0.0")
BUILD = os.getenv("RENDER_GIT_COMMIT", "0904beff")[:8]

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("multibot2.startup")

BR = "━━━━━━━━━━━━━━━━━━━━━━"


def telegram_send(token: str, chat_id: str, text: str) -> None:
    payload = parse.urlencode({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode()
    req = request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        method="POST",
    )
    with request.urlopen(req, timeout=20) as response:
        data = json.loads(response.read())
    if not data.get("ok"):
        raise RuntimeError(f"Telegram sendMessage failed: {data}")


def startup_message() -> str:
    return (
        f"🤖 *{APP_NAME} STARTED*\n"
        f"{BR}\n"
        f"🟢 Status: ONLINE\n"
        f"🏷 Version: `{APP_VERSION}`\n"
        f"🔖 Build: `{BUILD}`\n"
        f"🧪 Mode: PAPER\n"
        f"🇮🇳 Market: NSE-15\n"
        f"⏱ Timeframe: 1H\n"
        f"⏳ Signal freshness: 1h\n"
        f"💾 Persistence: Supabase\n"
        f"{BR}"
    )


def whats_new_message() -> str:
    return (
        "🆕 *WHAT'S NEW IN THIS BUILD*\n"
        f"{BR}\n"
        "📨 Complete Telegram command/message system\n"
        "📊 Original operational commands restored\n"
        "🟢🔴 Approved signal message templates\n"
        "🔔 Persistent one-hour signal reminders\n"
        "🎉💀 Trade WIN/LOSS close messages\n"
        "💾 Supabase persistence for bot state/history\n"
        "⛔ No `pending_sweeps` workflow\n"
        "🔒 Locked NSE-15 · 1H · 1h freshness rules\n"
        "🛡️ Paper-trading runtime remains enabled\n"
        f"{BR}"
    )


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.warning("Startup Telegram announcement skipped: Telegram credentials are missing")
        return 0

    try:
        telegram_send(token, chat_id, startup_message())
        telegram_send(token, chat_id, whats_new_message())
        logger.info("Startup announcements sent: version=%s build=%s", APP_VERSION, BUILD)
    except Exception as exc:
        logger.warning("Startup Telegram announcement failed: %s", exc)
        # Never prevent MULTIBOT2 itself from starting because an announcement failed.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
