import pandas as pd
from signal_gate import SignalGate
from strategies import StrategySignal
from trendpulse_runtime import TrendPulseRuntime

def make_1h_frame(days=20):
    timestamps=[]
    for day in pd.date_range("2026-08-03",periods=days,freq="D"):
        timestamps.extend([day+pd.Timedelta(hours=10,minutes=15),day+pd.Timedelta(hours=11,minutes=15),day+pd.Timedelta(hours=12,minutes=15),day+pd.Timedelta(hours=13,minutes=15),day+pd.Timedelta(hours=14,minutes=15),day+pd.Timedelta(hours=15,minutes=15)])
    index=pd.DatetimeIndex(timestamps).tz_localize("Asia/Kolkata");close=pd.Series([100.0+i for i in range(len(index))],index=index);return pd.DataFrame({"open":close-.5,"high":close+1,"low":close-1,"close":close},index=index)
def test_runtime_builds_confirmed_four_hour_groups():
    result=TrendPulseRuntime._build_4h(make_1h_frame());assert len(result)==20;assert all(result.index.hour==13);assert all(result.index.minute==15)
def test_runtime_4h_groups_do_not_cross_missing_hour():
    frame=make_1h_frame();frame=frame.drop(pd.Timestamp("2026-08-03 11:15:00+05:30"));result=TrendPulseRuntime._build_4h(frame);assert len(result)==19;assert pd.Timestamp("2026-08-03 13:15:00+05:30") not in result.index

def test_runtime_scan_does_not_consume_gate_by_default(monkeypatch):
    runtime=TrendPulseRuntime(gate=SignalGate());candles=make_1h_frame();signal=StrategySignal("TrendPulse","BUY",pd.Timestamp("2026-08-31 11:15:00+05:30"),"TEST",100,2);monkeypatch.setattr(runtime,"fetch_symbol_1h",lambda symbol,period="30d":candles);monkeypatch.setattr("trendpulse_runtime.trendpulse_from_frames",lambda one_h,four_h,completed_only=True:signal);result=runtime.scan_symbol("RELIANCE",now=pd.Timestamp("2026-08-31 12:00:00+05:30"));assert result.fresh and not result.accepted and result.reason=="READY_FOR_ACCEPTANCE";assert runtime.gate.repeat_count(signal,symbol="RELIANCE")==0
def test_runtime_accepts_fresh_signal_only_when_explicitly_requested(monkeypatch):
    runtime=TrendPulseRuntime(gate=SignalGate());candles=make_1h_frame();signal=StrategySignal("TrendPulse","BUY",pd.Timestamp("2026-08-31 11:15:00+05:30"),"TEST",100,2);monkeypatch.setattr(runtime,"fetch_symbol_1h",lambda symbol,period="30d":candles);monkeypatch.setattr("trendpulse_runtime.trendpulse_from_frames",lambda one_h,four_h,completed_only=True:signal);result=runtime.scan_symbol("RELIANCE",now=pd.Timestamp("2026-08-31 12:00:00+05:30"),accept_signal=True);assert result.accepted and result.reason=="ACCEPTED" and runtime.gate.repeat_count(signal,symbol="RELIANCE")==1
def test_runtime_rejects_stale_signal(monkeypatch):
    runtime=TrendPulseRuntime(gate=SignalGate());candles=make_1h_frame();signal=StrategySignal("TrendPulse","BUY",pd.Timestamp("2026-08-31 10:15:00+05:30"),"TEST",100,2);monkeypatch.setattr(runtime,"fetch_symbol_1h",lambda symbol,period="30d":candles);monkeypatch.setattr("trendpulse_runtime.trendpulse_from_frames",lambda one_h,four_h,completed_only=True:signal);result=runtime.scan_symbol("RELIANCE",now=pd.Timestamp("2026-08-31 12:00:01+05:30"),accept_signal=True);assert not result.accepted and result.reason=="STALE_SIGNAL"
def test_runtime_universe_is_exactly_fixed_nse15():
    from config import NSE_15_SYMBOLS
    assert len(NSE_15_SYMBOLS)==15 and len(set(NSE_15_SYMBOLS))==15
