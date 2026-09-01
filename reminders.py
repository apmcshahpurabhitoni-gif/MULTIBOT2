"""Independent one-hour reminder worker using the original approved signal message type."""
from __future__ import annotations
import json,threading
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
                metadata=json.loads(row.get("metadata") or "{}");message_type=str(metadata.get("message_type") or "MSG-REMINDER-V1");reminder=TelegramMessage(message_type,"🔔 REMINDER\n"+text);send_message(reminder,self._config());self.database.mark_reminder_sent(row["signal_key"],current.isoformat());sent+=1
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
