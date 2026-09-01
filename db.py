"""Single authoritative SQLite persistence layer for MULTIBOT2."""
from __future__ import annotations
import json
import os
import sqlite3
from typing import Any

DEFAULT_DB_PATH = os.getenv("BOT_STATE_DB_PATH", "multibot2_state.db")

class DatabaseError(RuntimeError):
    pass

class DatabaseManager:
    def __init__(self, path: str | None = None) -> None:
        self.path = path or DEFAULT_DB_PATH
        parent = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(parent, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS accounts (
                name TEXT PRIMARY KEY,
                starting_balance REAL NOT NULL,
                balance REAL NOT NULL,
                trades_today INTEGER NOT NULL DEFAULT 0,
                planned_risk_used REAL NOT NULL DEFAULT 0,
                reset_date TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS signals (
                signal_key TEXT PRIMARY KEY,
                send_count INTEGER NOT NULL DEFAULT 0,
                first_sent_at TEXT,
                last_sent_at TEXT,
                reminder_due_at TEXT,
                reminder_sent INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS pending_sweeps (
                signal_key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                due_at TEXT NOT NULL,
                sent INTEGER NOT NULL DEFAULT 0
            );
            """)

    def load_accounts(self, names: tuple[str, ...], starting_balance: float, today: str) -> dict[str, dict[str, Any]]:
        with self._connect() as conn:
            for name in names:
                row = conn.execute("SELECT * FROM accounts WHERE name=?", (name,)).fetchone()
                if row is None:
                    conn.execute("INSERT INTO accounts(name,starting_balance,balance,trades_today,planned_risk_used,reset_date) VALUES(?,?,?,?,?,?)", (name, starting_balance, starting_balance, 0, 0.0, today))
                elif row["reset_date"] != today:
                    conn.execute("UPDATE accounts SET trades_today=0, planned_risk_used=0, reset_date=? WHERE name=?", (today, name))
            conn.commit()
            rows = conn.execute("SELECT * FROM accounts WHERE name IN (%s)" % ",".join("?" for _ in names), names).fetchall()
        return {row["name"]: dict(row) for row in rows}

    def save_account(self, name: str, *, balance: float, trades_today: int, planned_risk_used: float, reset_date: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE accounts SET balance=?, trades_today=?, planned_risk_used=?, reset_date=? WHERE name=?", (balance, trades_today, planned_risk_used, reset_date, name))
            conn.commit()

    def save_trade(self, trade_id: str, status: str, payload: dict[str, Any], updated_at: str) -> None:
        with self._connect() as conn:
            conn.execute("INSERT INTO trades(id,status,payload,updated_at) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,payload=excluded.payload,updated_at=excluded.updated_at", (trade_id, status, json.dumps(payload, default=str), updated_at))
            conn.commit()

    def load_trades(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if status is None:
                rows = conn.execute("SELECT payload FROM trades ORDER BY updated_at DESC").fetchall()
            else:
                rows = conn.execute("SELECT payload FROM trades WHERE status=? ORDER BY updated_at DESC", (status,)).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def record_signal_send(self, signal_key: str, sent_at: str, reminder_due_at: str | None = None) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT send_count FROM signals WHERE signal_key=?", (signal_key,)).fetchone()
            if row is None:
                conn.execute("INSERT INTO signals(signal_key,send_count,first_sent_at,last_sent_at,reminder_due_at,reminder_sent) VALUES(?,?,?,?,?,0)", (signal_key, 1, sent_at, sent_at, reminder_due_at))
                count = 1
            else:
                count = min(int(row["send_count"]) + 1, 2)
                conn.execute("UPDATE signals SET send_count=?, last_sent_at=?, reminder_sent=? WHERE signal_key=?", (count, sent_at, 1 if count >= 2 else 0, signal_key))
            conn.commit()
        return count

    def signal_count(self, signal_key: str) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT send_count FROM signals WHERE signal_key=?", (signal_key,)).fetchone()
        return int(row["send_count"]) if row else 0

    def due_reminders(self, now_iso: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT signal_key,reminder_due_at FROM signals WHERE send_count=1 AND reminder_sent=0 AND reminder_due_at IS NOT NULL AND reminder_due_at<=?", (now_iso,)).fetchall()
        return [dict(row) for row in rows]

    def mark_reminder_sent(self, signal_key: str, sent_at: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE signals SET send_count=2, reminder_sent=1, last_sent_at=? WHERE signal_key=? AND send_count=1", (sent_at, signal_key))
            conn.commit()

    def save_pending_sweep(self, signal_key: str, payload: dict[str, Any], due_at: str) -> None:
        with self._connect() as conn:
            conn.execute("INSERT OR REPLACE INTO pending_sweeps(signal_key,payload,due_at,sent) VALUES(?,?,?,0)", (signal_key, json.dumps(payload, default=str), due_at))
            conn.commit()

    def due_pending_sweeps(self, now_iso: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT signal_key,payload,due_at FROM pending_sweeps WHERE sent=0 AND due_at<=?", (now_iso,)).fetchall()
        return [{"signal_key": row["signal_key"], "payload": json.loads(row["payload"]), "due_at": row["due_at"]} for row in rows]

    def mark_pending_sweep_sent(self, signal_key: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE pending_sweeps SET sent=1 WHERE signal_key=?", (signal_key,))
            conn.commit()

    def close(self) -> None:
        return None

__all__ = ["DatabaseError", "DatabaseManager"]
