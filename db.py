"""Authoritative persistence: local SQLite cache plus Supabase production durability."""
from __future__ import annotations
import json, os, sqlite3
from datetime import datetime, timezone
from typing import Any
from urllib import error, parse, request

DEFAULT_DB_PATH = os.getenv("BOT_STATE_DB_PATH", "/tmp/workspace/multibot2_state.db")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

class DatabaseError(RuntimeError):
    pass

class DatabaseManager:
    def __init__(self, path: str | None = None) -> None:
        self.path = path or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        self._initialize()
        self._restore_from_supabase_if_needed()

    @property
    def supabase_enabled(self) -> bool:
        return bool(SUPABASE_URL and SUPABASE_KEY)

    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as c:
            c.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS accounts(name TEXT PRIMARY KEY, starting_balance REAL NOT NULL, balance REAL NOT NULL, trades_today INTEGER NOT NULL DEFAULT 0, planned_risk_used REAL NOT NULL DEFAULT 0, reset_date TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS trades(id TEXT PRIMARY KEY, status TEXT NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS signals(signal_key TEXT PRIMARY KEY, send_count INTEGER NOT NULL DEFAULT 0, first_sent_at TEXT, last_sent_at TEXT, reminder_due_at TEXT, reminder_sent INTEGER NOT NULL DEFAULT 0, message_text TEXT, metadata TEXT);
            """)
            c.commit()

    def _supabase_request(self, method: str, table: str, *, params: str = "", data: Any = None, upsert: bool = False) -> Any:
        if not self.supabase_enabled:
            return None
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        if params:
            url += "?" + params
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json", "Accept": "application/json", "Prefer": "return=representation"}
        if upsert:
            headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        body = None if data is None else json.dumps(data, default=str).encode()
        try:
            with request.urlopen(request.Request(url, data=body, headers=headers, method=method), timeout=10) as response:
                raw = response.read().decode()
                return json.loads(raw) if raw else True
        except (error.HTTPError, error.URLError, TimeoutError, ValueError) as exc:
            print(f"[DB WARN] Supabase {method} {table} failed: {exc}")
            return None

    def _restore_from_supabase_if_needed(self) -> None:
        if not self.supabase_enabled:
            return
        with self._connect() as c:
            local_has_data = any(c.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone() for table in ("accounts", "trades", "signals"))
        if local_has_data:
            return
        self._restore_accounts(); self._restore_trades(); self._restore_signals()

    def _restore_accounts(self) -> None:
        rows = self._supabase_request("GET", "accounts", params="select=*") or []
        with self._connect() as c:
            for row in rows:
                name = row.get("name")
                if not name: continue
                starting = float(row.get("starting_balance", row.get("balance", 100000.0)) or 100000.0)
                balance = float(row.get("balance", starting) or starting)
                trades = int(row.get("daily_trades", row.get("trades_today", 0)) or 0)
                reset = str(row.get("last_reset_date", row.get("reset_date", "")) or "")
                planned = float(row.get("planned_risk_used", 0) or 0)
                c.execute("INSERT OR REPLACE INTO accounts VALUES(?,?,?,?,?,?)", (name, starting, balance, trades, planned, reset))
            c.commit()

    def _restore_trades(self) -> None:
        for table, status in (("active_trades", "OPEN"), ("closed_trades", "CLOSED")):
            rows = self._supabase_request("GET", table, params="select=*") or []
            with self._connect() as c:
                for row in rows:
                    trade_id = str(row.get("id", ""))
                    if not trade_id: continue
                    payload = {"id": trade_id, "status": status, "symbol": row.get("symbol", ""), "market": row.get("market", "NSE"), "account": row.get("account", ""), "strategy": row.get("strat", row.get("strategy", "")), "type": row.get("type", "LONG"), "entry": float(row.get("entry", 0) or 0), "sl": float(row.get("sl", 0) or 0), "tp": float(row.get("tp", 0) or 0), "qty": float(row.get("qty", 0) or 0), "trail_sl": float(row.get("trail_sl", row.get("sl", 0)) or 0), "signal_ts": row.get("ts_trigger", 0), "opened_at": row.get("opened_at", ""), "time": row.get("time_str", row.get("time", ""))}
                    if status == "CLOSED": payload.update({"exit_price": float(row.get("exit_price", 0) or 0), "pnl": float(row.get("pnl", 0) or 0), "result": row.get("result", ""), "exit_reason": row.get("exit_reason", ""), "closed_at": row.get("closed_at", row.get("close_time", ""))})
                    updated = payload.get("closed_at") or payload.get("opened_at") or datetime.now(timezone.utc).isoformat()
                    c.execute("INSERT OR REPLACE INTO trades VALUES(?,?,?,?)", (trade_id, status, json.dumps(payload, default=str), str(updated)))
                c.commit()

    def _restore_signals(self) -> None:
        rows = self._supabase_request("GET", "sent_signals", params="select=*") or []
        with self._connect() as c:
            for row in rows:
                key = str(row.get("sig_key", row.get("signal_key", "")))
                if not key: continue
                count = min(int(row.get("send_count", 0) or 0), 2)
                last_ts = row.get("last_sent_ts")
                last_sent = None
                if last_ts is not None:
                    try: last_sent = datetime.fromtimestamp(float(last_ts) / 1000, timezone.utc).isoformat()
                    except (TypeError, ValueError, OverflowError): pass
                c.execute("INSERT OR REPLACE INTO signals VALUES(?,?,?,?,?,?,?,?)", (key, count, last_sent, last_sent, None, int(count >= 2), None, "{}"))
            c.commit()

    def load_accounts(self, names: tuple[str, ...], starting_balance: float, today: str) -> dict[str, dict[str, Any]]:
        with self._connect() as c:
            for name in names:
                row = c.execute("SELECT * FROM accounts WHERE name=?", (name,)).fetchone()
                if row is None: c.execute("INSERT INTO accounts VALUES(?,?,?,?,?,?)", (name, starting_balance, starting_balance, 0, 0.0, today))
                elif row["reset_date"] != today: c.execute("UPDATE accounts SET trades_today=0,planned_risk_used=0,reset_date=? WHERE name=?", (today, name))
            c.commit(); rows = c.execute("SELECT * FROM accounts WHERE name IN (%s)" % ",".join("?" for _ in names), names).fetchall()
        return {row["name"]: dict(row) for row in rows}

    def save_account(self, name: str, *, balance: float, trades_today: int, planned_risk_used: float, reset_date: str) -> None:
        with self._connect() as c: c.execute("UPDATE accounts SET balance=?,trades_today=?,planned_risk_used=?,reset_date=? WHERE name=?", (balance, trades_today, planned_risk_used, reset_date, name)); c.commit()
        self._supabase_request("POST", "accounts", data={"name": name, "starting_balance": 100000.0, "balance": balance, "daily_trades": trades_today, "trades_today": trades_today, "planned_risk_used": planned_risk_used, "last_reset_date": reset_date, "reset_date": reset_date}, upsert=True)

    def save_trade(self, trade_id: str, status: str, payload: dict[str, Any], updated_at: str) -> None:
        with self._connect() as c: c.execute("INSERT INTO trades VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,payload=excluded.payload,updated_at=excluded.updated_at", (trade_id, status, json.dumps(payload, default=str), updated_at)); c.commit()
        if status == "OPEN":
            data={"id":trade_id,"symbol":payload.get("symbol",""),"market":payload.get("market","NSE"),"account":payload.get("account",""),"strat":payload.get("strategy",payload.get("strat","")),"type":payload.get("type","LONG"),"entry":payload.get("entry",0),"sl":payload.get("sl",0),"tp":payload.get("tp",0),"qty":payload.get("qty",0),"trail_sl":payload.get("trail_sl",payload.get("sl",0)),"ts_trigger":payload.get("signal_ts",0),"opened_at":payload.get("opened_at",updated_at),"time_str":payload.get("time",updated_at)}
            self._supabase_request("POST", "active_trades", data=data, upsert=True)
        else:
            self._supabase_request("DELETE", "active_trades", params=parse.urlencode({"id":f"eq.{trade_id}"}))
            data={"id":trade_id,"symbol":payload.get("symbol",""),"market":payload.get("market","NSE"),"account":payload.get("account",""),"strat":payload.get("strategy",payload.get("strat","")),"type":payload.get("type","LONG"),"entry":payload.get("entry",0),"exit_price":payload.get("exit_price",0),"pnl":payload.get("pnl",0),"result":payload.get("result",""),"exit_reason":payload.get("exit_reason",""),"close_time":payload.get("closed_at",updated_at),"closed_at":payload.get("closed_at",updated_at)}
            self._supabase_request("POST", "closed_trades", data=data, upsert=True)

    def load_trades(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as c:
            q="SELECT payload FROM trades" + (" WHERE status=?" if status else "") + " ORDER BY updated_at DESC"; rows=c.execute(q,(status,) if status else ()).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def record_signal_send(self, key: str, sent_at: str, reminder_due_at: str | None = None, message_text: str | None = None, metadata: dict | None = None) -> int:
        with self._connect() as c:
            row=c.execute("SELECT send_count FROM signals WHERE signal_key=?",(key,)).fetchone()
            if row is None: count=1; c.execute("INSERT INTO signals VALUES(?,?,?,?,?,?,?,?)",(key,1,sent_at,sent_at,reminder_due_at,0,message_text,json.dumps(metadata or {},default=str)))
            else: count=min(int(row["send_count"])+1,2); c.execute("UPDATE signals SET send_count=?,last_sent_at=?,reminder_sent=? WHERE signal_key=?",(count,sent_at,1 if count>=2 else 0,key))
            c.commit()
        self._supabase_request("POST", "sent_signals", data={"sig_key":key,"send_count":count,"last_sent_ts":int(_timestamp_ms(sent_at))}, upsert=True)
        return count

    def signal_count(self,key:str)->int:
        with self._connect() as c:r=c.execute("SELECT send_count FROM signals WHERE signal_key=?",(key,)).fetchone()
        return int(r["send_count"]) if r else 0

    def due_reminders(self,now_iso:str)->list[dict[str,Any]]:
        with self._connect() as c:rows=c.execute("SELECT * FROM signals WHERE send_count=1 AND reminder_sent=0 AND reminder_due_at IS NOT NULL AND reminder_due_at<=?",(now_iso,)).fetchall()
        return [dict(r) for r in rows]

    def mark_reminder_sent(self,key:str,sent_at:str)->None:
        with self._connect() as c:c.execute("UPDATE signals SET send_count=2,reminder_sent=1,last_sent_at=? WHERE signal_key=? AND send_count=1",(sent_at,key));c.commit()
        self._supabase_request("POST", "sent_signals", data={"sig_key":key,"send_count":2,"last_sent_ts":int(_timestamp_ms(sent_at))}, upsert=True)

def _timestamp_ms(value: str) -> float:
    try: return datetime.fromisoformat(value.replace("Z","+00:00")).timestamp()*1000
    except Exception: return datetime.now(timezone.utc).timestamp()*1000

__all__=["DatabaseError","DatabaseManager"]
