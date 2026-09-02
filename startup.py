"""MULTIBOT2 startup announcement.

Render runs this immediately before main.py so every process start announces
exactly which version/build is running and what changed in that release.
"""
from __future__ import annotations

import json
import logging
import os
from urllib import parse, request

APP_NAME = "MULTIBOT2"
APP_VERSION = os.getenv("MULTIBOT2_VERSION", "1.0.1")
BUILD = os.getenv("RENDER_GIT_COMMIT", "unknown")[:8]

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
        "🆕 *WHAT'S NEW — v1.0.1*\n"
        f"{BR}\n"
        "🛠️ *FIXED*\n"
        "🚫 TrendPulse NO_SIGNAL / NEUTRAL no longer sends `SIGNAL NOT SENT`\n"
        "🚫 Prevented the normal 15-symbol scan from generating 15 rejection messages\n"
        "🟡 Sweep neutral results are informational and no longer treated as trade rejections\n"
        "\n"
        "➕ *ADDED / IMPROVED*\n"
        "🔎 Scheduled Sweep checking messages\n"
        "⏱️ Canonical Sweep schedules for Crypto, Forex/Gold, NIFTY/BANKNIFTY and NSE\n"
        "🕯️ Original Sweep candle timing/close validation retained\n"
        "🚫 No FVG logic added\n"
        "🧭 Version/build identification on every bot restart\n"
        "📋 What's New now records fixes and additions per release\n"
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
