"""Independent one-hour reminder worker."""
from __future__ import annotations
import threading,time
import pandas as pd
from config import IST_TIMEZONE
from db import DatabaseManager
from telegram import TelegramConfig, TelegramMessage, send_message
class ReminderService:
    def __init__(self,database:DatabaseManager|None=None,telegram_config:TelegramConfig|None=None)->None:
        self.database=database or DatabaseManager(); self.telegram_config=telegram_config; self._stop=threading.Event()
    def _config(self):return self.telegram_config or TelegramConfig.from_env()
    def run_once(self,now:pd.Timestamp|None=None)->int:
        current=pd.Timestamp.now(tz=IST_TIMEZONE) if now is None else pd.Timestamp(now)
        if current.tzinfo is None:raise ValueError("Reminder time must be timezone-aware")
        current=current.tz_convert(IST_TIMEZONE); sent=0
        for row in self.database.due_reminders(current.isoformat()):
            text=row.get("message_text") or ""
            if not text:continue
            reminder=TelegramMessage("REMINDER", "🔔 REMINDER\n"+text)
            try:
                send_message(reminder,self._config()); self.database.mark_reminder_sent(row["signal_key"],current.isoformat()); sent+=1
            except Exception:continue
        return sent
    def start(self,interval_seconds:int=30)->threading.Thread:
        def loop():
            while not self._stop.is_set():
                try:self.run_once()
                finally:self._stop.wait(interval_seconds)
        thread=threading.Thread(target=loop,daemon=True,name="multibot2-reminders"); thread.start(); return thread
    def stop(self):self._stop.set()
__all__=["ReminderService"]
