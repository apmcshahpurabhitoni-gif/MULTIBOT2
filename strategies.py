"""Canonical strategy logic for MULTIBOT2."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
import pandas as pd
from candles import normalize_index
from config import IST_TIMEZONE
SignalType = Literal["BUY", "SELL", "NEUTRAL", "NO_SIGNAL"]

@dataclass(frozen=True)
class StrategySignal:
    strategy: str
    signal: SignalType
    timestamp: pd.Timestamp
    reason: str
    entry: float | None = None
    atr: float | None = None
    def __post_init__(self) -> None:
        ts = pd.Timestamp(self.timestamp)
        if ts.tzinfo is None: raise ValueError("Strategy signal timestamp must be timezone-aware")
        object.__setattr__(self, "timestamp", ts.tz_convert(IST_TIMEZONE))

def _validate_candle(candle: pd.Series, name: str) -> None:
    missing = [c for c in ("open","high","low","close") if c not in candle.index]
    if missing: raise ValueError(f"{name} candle missing: {', '.join(missing)}")
    if any(pd.isna(candle[c]) for c in ("open","high","low","close")): raise ValueError(f"{name} candle contains missing OHLC data")

def sweep_v2(previous: pd.Series, current: pd.Series, *, timestamp: pd.Timestamp) -> StrategySignal:
    _validate_candle(previous, "Previous"); _validate_candle(current, "Current")
    ts = pd.Timestamp(timestamp)
    if ts.tzinfo is None: raise ValueError("Strategy signal timestamp must be timezone-aware")
    ts = ts.tz_convert(IST_TIMEZONE)
    ph, pl = float(previous.high), float(previous.low); ch, cl, cc = float(current.high), float(current.low), float(current.close)
    if not (ch > ph and cl < pl): return StrategySignal("Sweep V2", "NO_SIGNAL", ts, "BOTH_SIDES_NOT_SWEPT")
    if cc > ph: return StrategySignal("Sweep V2", "BUY", ts, "BOTH_SIDES_SWEPT_CLOSE_ABOVE_PREVIOUS_HIGH")
    if cc < pl: return StrategySignal("Sweep V2", "SELL", ts, "BOTH_SIDES_SWEPT_CLOSE_BELOW_PREVIOUS_LOW")
    return StrategySignal("Sweep V2", "NEUTRAL", ts, "BOTH_SIDES_SWEPT_CLOSE_INSIDE_PREVIOUS_RANGE")

def sweep_v2_from_frame(candles: pd.DataFrame) -> StrategySignal:
    frame = normalize_index(candles)
    if len(frame) < 2:
        ts = frame.index[-1] if len(frame) else pd.Timestamp.now(tz=IST_TIMEZONE)
        return StrategySignal("Sweep V2", "NO_SIGNAL", ts, "INSUFFICIENT_DATA")
    return sweep_v2(frame.iloc[-2], frame.iloc[-1], timestamp=frame.index[-1])

def ema(series: pd.Series, period: int) -> pd.Series: return series.ewm(span=period, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff(); gain = delta.clip(lower=0).rolling(period).mean(); loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, pd.NA); result = (100 - 100 / (1 + rs)).astype(float); result = result.where(loss.ne(0), 100.0)
    return result.fillna(50.0)

def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series,pd.Series]:
    line = ema(series, fast) - ema(series, slow); return line, ema(line, signal)

def atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    pc = frame.close.shift(1); tr = pd.concat([frame.high-frame.low,(frame.high-pc).abs(),(frame.low-pc).abs()], axis=1).max(axis=1); return tr.rolling(period).mean()

def derive_4h_from_1h(candles_1h: pd.DataFrame) -> pd.DataFrame:
    frame = normalize_index(candles_1h)
    if frame.empty: return frame.copy()
    # 1H timestamps are candle-close labels. Four confirmed hourly closes form one confirmed 4H candle.
    rows=[]
    for day, group in frame.groupby(frame.index.date):
        group=group.sort_index()
        for start in range(0, len(group), 4):
            chunk=group.iloc[start:start+4]
            if len(chunk)!=4: continue
            rows.append({"timestamp":chunk.index[-1],"open":float(chunk.open.iloc[0]),"high":float(chunk.high.max()),"low":float(chunk.low.min()),"close":float(chunk.close.iloc[-1])})
    if not rows: return pd.DataFrame(columns=["open","high","low","close"], index=pd.DatetimeIndex([],tz=IST_TIMEZONE))
    out=pd.DataFrame(rows).set_index("timestamp"); out.index=pd.DatetimeIndex(out.index).tz_convert(IST_TIMEZONE); return out

def trendpulse_from_frames(candles_1h: pd.DataFrame, candles_4h: pd.DataFrame | None = None, *, completed_only: bool = True) -> StrategySignal:
    """Evaluate only confirmed candles. Caller controls raw/live versus completed input explicitly."""
    one=normalize_index(candles_1h); four=derive_4h_from_1h(one) if candles_4h is None else normalize_index(candles_4h)
    if len(one)<50 or len(four)<15:
        ts=one.index[-1] if len(one) else pd.Timestamp.now(tz=IST_TIMEZONE); return StrategySignal("TrendPulse","NO_SIGNAL",ts,"INSUFFICIENT_DATA")
    i=len(one)-2 if not completed_only else len(one)-1
    if i<26: return StrategySignal("TrendPulse","NO_SIGNAL",one.index[i],"INSUFFICIENT_CLOSED_CANDLES")
    ts=one.index[i]
    ema20=ema(one.close,20); rsi14=rsi(one.close,14); atr1=atr(one,14); ml,sl=macd(one.close)
    # Use the latest confirmed 4H candle whose close timestamp is <= the signal candle.
    eligible=four.loc[four.index<=ts]
    if len(eligible)<15: return StrategySignal("TrendPulse","NO_SIGNAL",ts,"INSUFFICIENT_CONFIRMED_4H_DATA")
    h=eligible.iloc[-1]; hts=eligible.index[-1]; hclose=four.close.loc[hts]; h_ema50=ema(four.close,50).loc[hts]; h_atr=atr(four,14).loc[hts]
    vals=[one.close.iloc[i],ema20.iloc[i],rsi14.iloc[i],atr1.iloc[i],ml.iloc[i-1],ml.iloc[i],sl.iloc[i-1],sl.iloc[i],hclose,h_ema50,h_atr]
    if any(pd.isna(x) for x in vals): return StrategySignal("TrendPulse","NO_SIGNAL",ts,"INDICATOR_DATA_UNAVAILABLE")
    if hclose<=0: return StrategySignal("TrendPulse","NO_SIGNAL",ts,"INVALID_HTF_CLOSE")
    if h_atr/hclose*100 < .2: return StrategySignal("TrendPulse","NO_SIGNAL",ts,"ATR_PERCENT_BELOW_0_2")
    bull=hclose>h_ema50 and ml.iloc[i-1]<=sl.iloc[i-1] and ml.iloc[i]>sl.iloc[i] and 50<rsi14.iloc[i]<80 and one.close.iloc[i]>ema20.iloc[i]
    bear=hclose<h_ema50 and ml.iloc[i-1]>=sl.iloc[i-1] and ml.iloc[i]<sl.iloc[i] and 20<rsi14.iloc[i]<50 and one.close.iloc[i]<ema20.iloc[i]
    if bull: return StrategySignal("TrendPulse","BUY",ts,"HTF_BULLISH_MACD_RSI_EMA_ALIGNMENT",entry=float(one.close.iloc[i]),atr=float(atr1.iloc[i]))
    if bear: return StrategySignal("TrendPulse","SELL",ts,"HTF_BEARISH_MACD_RSI_EMA_ALIGNMENT",entry=float(one.close.iloc[i]),atr=float(atr1.iloc[i]))
    return StrategySignal("TrendPulse","NO_SIGNAL",ts,"NO_APPROVED_ALIGNMENT")

def calc_sl_tp(signal: StrategySignal) -> tuple[float,float]:
    if signal.signal not in ("BUY","SELL") or signal.entry is None or signal.atr is None: raise ValueError("SL/TP requires a directional signal with entry and ATR")
    e=float(signal.entry); r=float(signal.atr)*1.5
    return (e-r,e+r*2) if signal.signal=="BUY" else (e+r,e-r*2)

__all__=["StrategySignal","sweep_v2","sweep_v2_from_frame","ema","rsi","macd","atr","derive_4h_from_1h","trendpulse_from_frames","calc_sl_tp"]
