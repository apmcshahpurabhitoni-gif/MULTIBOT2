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
APP_VERSION = os.getenv("MULTIBOT2_VERSION", "1.0.3")
BUILD = os.getenv("RENDER_GIT_COMMIT", "unknown")[:8]

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("multibot2.startup")
BR = "━━━━━━━━━━━━━━━━━━━━━━"


def telegram_send(token: str, chat_id: str, text: str) -> None:
    payload = parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    req = request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=payload, method="POST")
    with request.urlopen(req, timeout=20) as response:
        data = json.loads(response.read())
    if not data.get("ok"):
        raise RuntimeError(f"Telegram sendMessage failed: {data}")


def startup_message() -> str:
    return (
        f"🤖 {APP_NAME} STARTED\n{BR}\n"
        f"🟢 Status: ONLINE\n🏷 Version: {APP_VERSION}\n🔖 Build: {BUILD}\n"
        "🧪 Mode: PAPER\n🇮🇳 Market: NSE-15\n⏱ Timeframe: 1H\n"
        "⏳ Signal freshness: 1h\n💾 Persistence: Supabase\n" + BR
    )


def whats_new_message() -> str:
    return (
        f"🆕 WHAT'S NEW — v{APP_VERSION}\n{BR}\n"
        "🛠️ FIXED\n"
        "🚫 Automated TrendPulse NO_SIGNAL / NEUTRAL scans are silent\n"
        "🚫 Automated stale/duplicate/limit rejections no longer send SIGNAL NOT SENT spam\n"
        "🚫 A normal 15-symbol scan cannot produce 15 rejection notifications\n"
        "🟡 Sweep neutral results remain informational, not trade rejections\n\n"
        "➕ ADDED / IMPROVED\n"
        "🧪 Regression coverage for non-directional and rejection-silence behavior\n"
        "📨 Startup and What's New are sent independently\n"
        "🛡️ Startup announcements no longer depend on Markdown parsing\n"
        "🧭 Version/build is reported on every restart\n"
        "🚫 No FVG logic added\n" + BR
    )


def _send_startup_notice(token: str, chat_id: str, label: str, text: str) -> None:
    try:
        telegram_send(token, chat_id, text)
        logger.info("%s announcement sent: version=%s build=%s", label, APP_VERSION, BUILD)
    except Exception as exc:
        logger.warning("%s announcement failed: %s", label, exc)


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.warning("Startup Telegram announcement skipped: Telegram credentials are missing")
        return 0
    _send_startup_notice(token, chat_id, "startup", startup_message())
    _send_startup_notice(token, chat_id, "whats-new", whats_new_message())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
