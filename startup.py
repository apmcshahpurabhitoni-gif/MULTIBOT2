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
APP_VERSION = os.getenv("MULTIBOT2_VERSION", "1.0.8")
BUILD = os.getenv("RENDER_GIT_COMMIT", "unknown")[:8]
DASHBOARD_URL = "https://multibot2-t74l.onrender.com/dashboard"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("multibot2.startup")
BR = "━━━━━━━━━━━━━━━━━━━━━━"


def telegram_send(token: str, chat_id: str, text: str) -> None:
    payload = parse.urlencode({"chat_id": chat_id, "text": text}).encode()
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
        f"🤖 {APP_NAME} STARTED\n{BR}\n"
        f"🟢 Status: ONLINE\n🏷 Version: {APP_VERSION}\n🔖 Build: {BUILD}\n"
        "🧪 Mode: PAPER\n🇮🇳 Market: NSE-15\n⏱ Timeframe: 1H\n"
        "⏳ Signal freshness: 1h\n💾 Persistence: Supabase\n\n"
        f"🌐 DASHBOARD\n👉 {DASHBOARD_URL}\n" + BR
    )


def whats_new_message() -> str:
    return (
        f"🆕 WHAT'S NEW — v{APP_VERSION}\n{BR}\n"
        "➕ ADDED / IMPROVED\n"
        "🌐 Dashboard link now opens the actual /dashboard page\n"
        "⚡ One tap from Telegram opens the live dashboard\n"
        "🎨 Premium dashboard visual hierarchy and responsive presentation\n\n"
        "🛠️ FIXED / PRESERVED\n"
        "🔗 Fixed the missing /dashboard server route that caused Not Found\n"
        "📐 Stronger dashboard cards, spacing, navigation and visual depth\n"
        "📱 Improved mobile dashboard presentation\n"
        "🌙 Dark and Neo-Brutalist themes preserved\n"
        "🚫 No trading strategy, execution, risk, persistence or Telegram signal behavior changed\n"
        "🚫 No FVG logic added\n" + BR
    )


def _send_notice(
    token: str,
    chat_id: str,
    label: str,
    text: str,
) -> None:
    try:
        telegram_send(token, chat_id, text)
        logger.info(
            "%s announcement sent: version=%s build=%s",
            label,
            APP_VERSION,
            BUILD,
        )
    except Exception as exc:
        logger.warning("%s announcement failed: %s", label, exc)


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.warning(
            "Startup Telegram announcement skipped: Telegram credentials are missing"
        )
        return 0

    _send_notice(token, chat_id, "startup", startup_message())
    _send_notice(token, chat_id, "whats-new", whats_new_message())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
