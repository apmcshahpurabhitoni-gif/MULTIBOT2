"""Single authoritative SQLite persistence layer for MULTIBOT2."""
from __future__ import annotations
import json, os, sqlite3
from typing import Any
DEFAULT_DB_PATH=os.getenv("BOT_STATE_DB_PATH","multibot2_state.db")
class DatabaseError(RuntimeError): pass
class DatabaseManager:
    def __init__(self,path:str|None=None)->None:
        self.path=path or DEFAULT_DB_PATH; os.makedirs(os.path.dirname(os.path.abspath(self.path)),exist_ok=True); self._initialize()
    def _connect(self):
        c=sqlite3.connect(self.path,timeout=30); c.row_factory=sqlite3.Row; return c
    def _initialize(self):
        with self._connect() as c:
            c.executescript("""PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS accounts(name TEXT PRIMARY KEY,starting_balance REAL NOT NULL,balance REAL NOT NULL,trades_today INTEGER NOT NULL DEFAULT 0,planned_risk_used REAL NOT NULL DEFAULT 0,reset_date TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS trades(id TEXT PRIMARY KEY,status TEXT NOT NULL,payload TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS signals(signal_key TEXT PRIMARY KEY,send_count INTEGER NOT NULL DEFAULT 0,first_sent_at TEXT,last_sent_at TEXT,reminder_due_at TEXT,reminder_sent INTEGER NOT NULL DEFAULT 0,message_text TEXT,metadata TEXT);
CREATE TABLE IF NOT EXISTS pending_sweeps(signal_key TEXT PRIMARY KEY,payload TEXT NOT NULL,due_at TEXT NOT NULL,sent INTEGER NOT NULL DEFAULT 0);""")
            cols={r[1] for r in c.execute("PRAGMA table_info(signals)")}
            if "message_text" not in cols:c.execute("ALTER TABLE signals ADD COLUMN message_text TEXT")
            if "metadata" not in cols:c.execute("ALTER TABLE signals ADD COLUMN metadata TEXT")
            c.commit()
    def load_accounts(self,names:tuple[str,...],starting_balance:float,today:str)->dict[str,dict[str,Any]]:
        with self._connect() as c:
            for n in names:
                r=c.execute("SELECT * FROM accounts WHERE name=?",(n,)).fetchone()
                if r is None:c.execute("INSERT INTO accounts VALUES(?,?,?,?,?,?)",(n,starting_balance,starting_balance,0,0.0,today))
                elif r["reset_date"]!=today:c.execute("UPDATE accounts SET trades_today=0,planned_risk_used=0,reset_date=? WHERE name=?",(today,n))
            c.commit(); rows=c.execute("SELECT * FROM accounts WHERE name IN (%s)"%','.join('?' for _ in names),names).fetchall()
        return {r["name"]:dict(r) for r in rows}
    def save_account(self,name:str,*,balance:float,trades_today:int,planned_risk_used:float,reset_date:str)->None:
        with self._connect() as c:c.execute("UPDATE accounts SET balance=?,trades_today=?,planned_risk_used=?,reset_date=? WHERE name=?",(balance,trades_today,planned_risk_used,reset_date,name)); c.commit()
    def save_trade(self,trade_id:str,status:str,payload:dict[str,Any],updated_at:str)->None:
        with self._connect() as c:c.execute("INSERT INTO trades VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,payload=excluded.payload,updated_at=excluded.updated_at",(trade_id,status,json.dumps(payload,default=str),updated_at)); c.commit()
    def load_trades(self,status:str|None=None)->list[dict[str,Any]]:
        with self._connect() as c:
            q="SELECT payload FROM trades"+(" WHERE status=?" if status else "")+" ORDER BY updated_at DESC"; rows=c.execute(q,(status,) if status else ()).fetchall()
        return [json.loads(r["payload"]) for r in rows]
    def record_signal_send(self,key:str,sent_at:str,reminder_due_at:str|None=None,message_text:str|None=None,metadata:dict|None=None)->int:
        with self._connect() as c:
            r=c.execute("SELECT send_count FROM signals WHERE signal_key=?",(key,)).fetchone()
            if r is None:c.execute("INSERT INTO signals(signal_key,send_count,first_sent_at,last_sent_at,reminder_due_at,reminder_sent,message_text,metadata) VALUES(?,?,?,?,?,?,?,?)",(key,1,sent_at,sent_at,reminder_due_at,0,message_text,json.dumps(metadata or {},default=str))); count=1
            else: count=min(int(r["send_count"])+1,2); c.execute("UPDATE signals SET send_count=?,last_sent_at=?,reminder_sent=? WHERE signal_key=?",(count,sent_at,1 if count>=2 else 0,key))
            c.commit(); return count
    def signal_count(self,key:str)->int:
        with self._connect() as c:r=c.execute("SELECT send_count FROM signals WHERE signal_key=?",(key,)).fetchone()
        return int(r["send_count"]) if r else 0
    def due_reminders(self,now_iso:str)->list[dict[str,Any]]:
        with self._connect() as c: rows=c.execute("SELECT * FROM signals WHERE send_count=1 AND reminder_sent=0 AND reminder_due_at IS NOT NULL AND reminder_due_at<=?",(now_iso,)).fetchall()
        return [dict(r) for r in rows]
    def mark_reminder_sent(self,key:str,sent_at:str)->None:
        with self._connect() as c:c.execute("UPDATE signals SET send_count=2,reminder_sent=1,last_sent_at=? WHERE signal_key=? AND send_count=1",(sent_at,key)); c.commit()
    def save_pending_sweep(self,key:str,payload:dict[str,Any],due_at:str)->None:
        with self._connect() as c:c.execute("INSERT OR REPLACE INTO pending_sweeps VALUES(?,?,?,0)",(key,json.dumps(payload,default=str),due_at)); c.commit()
    def due_pending_sweeps(self,now_iso:str)->list[dict[str,Any]]:
        with self._connect() as c:rows=c.execute("SELECT * FROM pending_sweeps WHERE sent=0 AND due_at<=?",(now_iso,)).fetchall()
        return [{"signal_key":r["signal_key"],"payload":json.loads(r["payload"]),"due_at":r["due_at"]} for r in rows]
    def mark_pending_sweep_sent(self,key:str)->None:
        with self._connect() as c:c.execute("UPDATE pending_sweeps SET sent=1 WHERE signal_key=?",(key,)); c.commit()
__all__=["DatabaseError","DatabaseManager"]
