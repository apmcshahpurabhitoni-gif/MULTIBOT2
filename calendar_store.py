"""One-fetch-per-IST-day persistent cache for the Forex Factory calendar."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
DEFAULT_PATH = os.getenv("BOT_STATE_DB_PATH", "/tmp/workspace/multibot2_state.db")


class CalendarStore:
    """Persist calendar data and the daily fetch attempt so refreshes never hammer the feed."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path or DEFAULT_PATH
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS forex_calendar_cache (feed_key TEXT PRIMARY KEY, fetched_date TEXT NOT NULL, fetched_at TEXT NOT NULL, events TEXT NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS forex_calendar_attempts (feed_key TEXT PRIMARY KEY, attempt_date TEXT NOT NULL, attempted_at TEXT NOT NULL, error TEXT NOT NULL)")
            conn.commit()

    @staticmethod
    def today_key() -> str:
        return datetime.now(IST).date().isoformat()

    def load_for_today(self, feed_key: str) -> tuple[list[dict] | None, str | None]:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT events, fetched_at FROM forex_calendar_cache WHERE feed_key=? AND fetched_date=?", (feed_key, self.today_key())).fetchone()
        if not row:
            return None, None
        try:
            events = json.loads(row[0])
        except (TypeError, ValueError):
            return None, None
        return (events if isinstance(events, list) else None), row[1]

    def save_today(self, feed_key: str, events: list[dict]) -> str:
        fetched_at = datetime.now(IST).isoformat()
        with sqlite3.connect(self.path) as conn:
            conn.execute("INSERT INTO forex_calendar_cache(feed_key,fetched_date,fetched_at,events) VALUES(?,?,?,?) ON CONFLICT(feed_key) DO UPDATE SET fetched_date=excluded.fetched_date,fetched_at=excluded.fetched_at,events=excluded.events", (feed_key, self.today_key(), fetched_at, json.dumps(events, default=str)))
            conn.execute("DELETE FROM forex_calendar_attempts WHERE feed_key=?", (feed_key,))
            conn.commit()
        return fetched_at

    def save_attempt(self, feed_key: str, error: str) -> str:
        attempted_at = datetime.now(IST).isoformat()
        with sqlite3.connect(self.path) as conn:
            conn.execute("INSERT INTO forex_calendar_attempts(feed_key,attempt_date,attempted_at,error) VALUES(?,?,?,?) ON CONFLICT(feed_key) DO UPDATE SET attempt_date=excluded.attempt_date,attempted_at=excluded.attempted_at,error=excluded.error", (feed_key, self.today_key(), attempted_at, error))
            conn.commit()
        return attempted_at

    def load_attempt_for_today(self, feed_key: str) -> tuple[str, str] | None:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT attempted_at, error FROM forex_calendar_attempts WHERE feed_key=? AND attempt_date=?", (feed_key, self.today_key())).fetchone()
        return (row[0], row[1]) if row else None

    def load_latest(self, feed_key: str) -> tuple[list[dict] | None, str | None]:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT events, fetched_at FROM forex_calendar_cache WHERE feed_key=?", (feed_key,)).fetchone()
        if not row:
            return None, None
        try:
            events = json.loads(row[0])
        except (TypeError, ValueError):
            return None, None
        return (events if isinstance(events, list) else None), row[1]
