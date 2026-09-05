import pandas as pd
from db import DatabaseManager
from signal_gate import SignalGate
from strategies import StrategySignal
from sweep_service import SweepService
from trading import AccountState

def signal(ts="2026-09-01 15:00:00+05:30",direction="BUY"):
    return StrategySignal("Sweep V2",direction,pd.Timestamp(ts),"TEST")

def frame():
    # Canonical NSE Sweep V2 schedule: completed 09:15-13:15 and 13:15-15:15
    # The fixture supplies two complete hourly-aligned session segments so the
    # engine can build both the previous and current sweep candles.
    idx=pd.date_range("2026-09-01 09:15",periods=6,freq="1h",tz="Asia/Kolkata")
    return pd.DataFrame({
        "open":[100,101,99,100,100,101],
        "high":[105,106,104,103,110,111],
        "low":[95,96,94,93,90,89],
        "close":[101,99,100,100,108,111],
    },index=idx)

def service(tmp_path):
    db=DatabaseManager(str(tmp_path/"state.db")); accounts={"sweep_4h":AccountState("sweep_4h"),"macro":AccountState("macro"),"nifty":AccountState("nifty"),"ny_session":AccountState("ny_session")}; return SweepService(database=db,accounts=accounts)

def test_send_false_does_not_consume_gate(tmp_path):
    s=service(tmp_path); sig=signal(); result=s.dispatch("RELIANCE",sig,frame(),current_price=100,now=pd.Timestamp("2026-09-01 15:30+05:30"),send=False)
    assert result.reason=="READY_TO_SEND" and not result.sent and s.database.signal_count(s.gate.signal_key(sig,symbol="RELIANCE"))==0

def test_non_directional_signal_is_silent(tmp_path):
    s=service(tmp_path); result=s.dispatch("RELIANCE",signal(direction="NEUTRAL"),frame(),current_price=100,now=pd.Timestamp("2026-09-01 15:30+05:30"),send=False)
    assert result.reason=="NO_DIRECTIONAL_SIGNAL" and not result.sent
