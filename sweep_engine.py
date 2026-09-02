"""Canonical Sweep candle engine copied from the verified original repository.
No FVG logic: Sweep is only the two-sided liquidity sweep plus close classification.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
from config import IST_TIMEZONE, LIVE_ASSET_MAP

@dataclass(frozen=True)
class SweepResult:
    direction:str; timeframe:str; candle_start:pd.Timestamp; candle_end:pd.Timestamp; previous:dict; current:dict; high_swept:bool; low_swept:bool; schedule_warning:str|None=None

def _ist(df):
    out=df.copy();idx=pd.DatetimeIndex(out.index);idx=idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert(IST_TIMEZONE);out.index=idx;return out.sort_index()
def _ohlc(g):return {"open":float(g.open.iloc[0]),"high":float(g.high.max()),"low":float(g.low.min()),"close":float(g.close.iloc[-1])}
def _starts(now,hours,minute):
    out=[];day=now.normalize()-pd.Timedelta(days=3)
    while day<=now.normalize():
        for h in hours:out.append(day+pd.Timedelta(hours=h,minutes=minute))
        day+=pd.Timedelta(days=1)
    return out
def _explicit(df,starts,duration,now):
    rows=[]
    for start in starts:
        end=start+duration
        if end>now:continue
        g = df[(df.index >= start) & (df.index < end)].sort_index()
        if g.empty:
            continue
        expected_count = 1 if duration == pd.Timedelta(hours=1) else int(duration / pd.Timedelta(hours=1))
        if expected_count > 1:
            expected = pd.date_range(
                start=start,
                periods=expected_count,
                freq="1h",
                tz=IST_TIMEZONE,
            )
            if len(g) != expected_count or not g.index.equals(expected):
                continue
        rows.append({"timestamp": start, **_ohlc(g)})
    if not rows:return pd.DataFrame(columns=["open","high","low","close"],index=pd.DatetimeIndex([],tz=IST_TIMEZONE))
    return pd.DataFrame(rows).set_index("timestamp").sort_index()
def build_closed_candles(df,symbol,now=None):
    if df is None or df.empty:return pd.DataFrame(),"","No market data"
    symbol = str(symbol).strip().upper()
    asset = LIVE_ASSET_MAP.get(symbol)
    is_equity = bool(asset and asset.asset_type == "equity") or symbol.endswith(".NS")
    now=pd.Timestamp(now or datetime.now().astimezone());now=now.tz_localize(IST_TIMEZONE) if now.tzinfo is None else now.tz_convert(IST_TIMEZONE);x=_ist(df)
    if symbol in ("^NSEI","^NSEBANK"):return _explicit(x,_starts(now,(9,10,11,12,13,14),15),pd.Timedelta(hours=1),now),"1H",None
    if is_equity:
        rows=[]
        for day,g in x.groupby(x.index.date):
            base=pd.Timestamp(day).tz_localize(IST_TIMEZONE);a=g[(g.index>=base+pd.Timedelta(hours=9,minutes=15))&(g.index<base+pd.Timedelta(hours=13,minutes=15))];b=g[(g.index>=base+pd.Timedelta(hours=13,minutes=15))&(g.index<base+pd.Timedelta(hours=15,minutes=15))]
            if not a.empty:rows.append((base+pd.Timedelta(hours=9,minutes=15),_ohlc(a),base+pd.Timedelta(hours=13,minutes=15)))
            if not b.empty and b.index.max()>=base+pd.Timedelta(hours=14,minutes=15):rows.append((base+pd.Timedelta(hours=13,minutes=15),_ohlc(b),base+pd.Timedelta(hours=15,minutes=15)))
        if not rows:return pd.DataFrame(),"4H","No complete NSE session bars"
        out=pd.DataFrame([{**v,"timestamp":s} for s,v,_ in rows]).set_index("timestamp");ends=pd.Series([e for _,_,e in rows],index=out.index);return out[ends<=now],"4H",None
    if symbol=="BTC-USD":return _explicit(x,_starts(now,(1,5,9,13,17,21),30),pd.Timedelta(hours=4),now),"4H",None
    return _explicit(x,_starts(now,(2,6,10,14,18,22),30),pd.Timedelta(hours=4),now),"4H",None
def detect_sweep(df,symbol,now=None):
    bars,tf,warning=build_closed_candles(df,symbol,now)
    if len(bars)<2:return None
    asset = LIVE_ASSET_MAP.get(str(symbol).strip().upper())
    is_equity = bool(asset and asset.asset_type == "equity") or str(symbol).strip().upper().endswith(".NS")
    prev,cur=bars.iloc[-2],bars.iloc[-1];start=pd.Timestamp(bars.index[-1]);end=start+(pd.Timedelta(hours=2) if is_equity and start.hour==13 else pd.Timedelta(hours=1) if tf=='1H' else pd.Timedelta(hours=4));hs=float(cur.high)>float(prev.high);ls=float(cur.low)<float(prev.low)
    if not(hs and ls):return None
    close=float(cur.close);direction="BULLISH" if close>float(prev.high) else "BEARISH" if close<float(prev.low) else "NEUTRAL";expected_minute=15 if is_equity or symbol in ('^NSEI','^NSEBANK') else 30;expected={9,13} if is_equity else {9,10,11,12,13,14} if symbol in ('^NSEI','^NSEBANK') else {1,5,9,13,17,21} if symbol=='BTC-USD' else {2,6,10,14,18,22}
    if start.hour not in expected or start.minute!=expected_minute:warning=f"Candle start {start.strftime('%H:%M IST')} is outside configured schedule"
    return SweepResult(direction,tf,start,end,{k:float(prev[k]) for k in ('open','high','low','close')},{k:float(cur[k]) for k in ('open','high','low','close')},hs,ls,warning)
