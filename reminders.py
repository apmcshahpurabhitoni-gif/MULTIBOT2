"""Independent one-hour reminder worker using the same approved signal template."""
from __future__ import annotations
import threading
import pandas as pd
from config import IST_TIMEZONE
from db import DatabaseManager
from telegram import TelegramConfig,TelegramMessage,send_message
class ReminderService:
    def __init__(self,database=None,telegram_config=None):self.database=database or DatabaseManager();self.telegram_config=telegram_config;self._stop=threading.Event()
    def _config(self):return self.telegram_config or TelegramConfig.from_env()
    def run_once(self,now=None):
        current=pd.Timestamp.now(tz=IST_TIMEZONE) if now is None else pd.Timestamp(now)
        if current.tzinfo is None:raise ValueError("Reminder time must be timezone-aware")
        current=current.tz_convert(IST_TIMEZONE);sent=0
        for row in self.database.due_reminders(current.isoformat()):
            text=row.get("message_text") or ""
            if not text:continue
            try:
                # Preserve the original approved message body/type; only prepend the reminder marker.
                message_type=str((row.get("metadata") or "")).split("strategy")[-1] if False else "REMINDER"
                reminder=TelegramMessage("MSG-REMINDER-V1", "🔔 REMINDER\n"+text);send_message(reminder,self._config());self.database.mark_reminder_sent(row["signal_key"],current.isoformat());sent+=1
            except Exception:continue
        return sent
    def start(self,interval_seconds=30):
        def loop():
            while not self._stop.is_set():
                try:self.run_once()
                finally:self._stop.wait(interval_seconds)
        t=threading.Thread(target=loop,daemon=True,name="multibot2-reminders");t.start();return t
    def stop(self):self._stop.set()
__all__=["ReminderService"]
