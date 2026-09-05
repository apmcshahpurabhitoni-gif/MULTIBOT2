"""Canonical signal freshness and duplicate gate for MULTIBOT2."""
from __future__ import annotations
from dataclasses import dataclass,field
from threading import RLock
import pandas as pd
from config import SIGNAL_FRESHNESS_HOURS,IST_TIMEZONE
from strategies import Signal
MAX_MESSAGE_SEND_COUNT=2
@dataclass
class SignalGate:
    max_age_hours:float=SIGNAL_FRESHNESS_HOURS
    max_repeats:int=MAX_MESSAGE_SEND_COUNT
    _counts:dict[str,int]=field(default_factory=dict)
    _lock:RLock=field(default_factory=RLock,repr=False)
    def __post_init__(self):
        if self.max_age_hours!=SIGNAL_FRESHNESS_HOURS:raise ValueError("MULTIBOT2 freshness is locked at 1 hour")
        if self.max_repeats!=MAX_MESSAGE_SEND_COUNT:raise ValueError("MULTIBOT2 maximum signal sends is locked at 2")
    @staticmethod
    def _ts(value):
        ts=pd.Timestamp(value)
        if ts.tzinfo is None:raise ValueError("Timestamp must be timezone-aware")
        return ts.tz_convert(IST_TIMEZONE)
    def age_hours(self,signal:Signal,*,now:pd.Timestamp|None=None)->float:
        ts=self._ts(signal.timestamp); current=self._ts(pd.Timestamp.now(tz=IST_TIMEZONE) if now is None else now); age=(current-ts).total_seconds()/3600
        if age<0:raise ValueError("Signal timestamp cannot be in the future")
        return age
    def is_fresh(self,signal:Signal,*,now:pd.Timestamp|None=None)->bool:return self.age_hours(signal,now=now)<=1
    @classmethod
    def signal_key(cls,signal:Signal,*,symbol:str)->str:
        symbol=symbol.strip().upper()
        if not symbol:raise ValueError("Signal symbol cannot be empty")
        return "|".join((signal.strategy,symbol,signal.direction,cls._ts(signal.timestamp).isoformat()))
    def repeat_count(self,signal:Signal,*,symbol:str)->int:
        with self._lock:return self._counts.get(self.signal_key(signal,symbol=symbol),0)
    def can_send(self,signal:Signal,*,symbol:str,now:pd.Timestamp|None=None)->bool:
        return signal.direction in ("BUY","SELL","NEUTRAL") and self.is_fresh(signal,now=now) and self.repeat_count(signal,symbol=symbol)<2
    def accept(self,signal:Signal,*,symbol:str,now:pd.Timestamp|None=None)->bool:
        if not self.can_send(signal,symbol=symbol,now=now):return False
        key=self.signal_key(signal,symbol=symbol)
        with self._lock:
            count=self._counts.get(key,0)
            if count>=2:return False
            self._counts[key]=count+1;return True
    def clear(self):
        with self._lock:self._counts.clear()
    def snapshot(self):
        with self._lock:return dict(self._counts)
    def restore(self,counts:dict[str,int]):
        if not isinstance(counts,dict):raise TypeError("Signal counts must be a dictionary")
        with self._lock:self._counts={k:min(max(int(v),0),2) for k,v in counts.items() if isinstance(k,str)}

def signal_status(signal:Signal,*,now:pd.Timestamp|None=None)->tuple[str,float]:
    gate=SignalGate();age=gate.age_hours(signal,now=now);return ("FRESH" if age<=1 else "STALE",age)
__all__=["SignalGate","MAX_MESSAGE_SEND_COUNT","signal_status"]
