import pandas as pd
from signal_gate import SignalGate
from strategies import StrategySignal
from trendpulse_runtime import TrendPulseRuntime

def make_1h_frame(rows=60):
    index=pd.date_range("2026-08-31 09:15:00+05:30",periods=rows,freq="1h");close=pd.Series([100.0+i for i in range(rows)],index=index);return pd.DataFrame({"open":close-.5,"high":close+1,"low":close-1,"close":close},index=index)
def test_runtime_builds_confirmed_four_hour_groups():
    result=TrendPulseRuntime._build_4h(make_1h_frame(60));assert not result.empty
    for _,group in result.groupby(result.index.date):assert len(group)<=3
    assert all((result.index[i]-result.index[i-1])==pd.Timedelta(hours=4) or result.index[i].date()!=result.index[i-1].date() for i in range(1,len(result)))
def test_runtime_4h_groups_do_not_cross_missing_hour():
    frame=make_1h_frame(60).drop(pd.Timestamp("2026-09-01 11:15:00+05:30"));result=TrendPulseRuntime._build_4h(frame);assert not result.empty
    assert all(result.index[i].date()!=result.index[i-1].date() or result.index[i]-result.index[i-1]==pd.Timedelta(hours=4) for i in range(1,len(result)))
def test_runtime_scan_does_not_consume_gate_by_default(monkeypatch):
    runtime=TrendPulseRuntime(gate=SignalGate());candles=make_1h_frame(60);signal=StrategySignal("TrendPulse","BUY",pd.Timestamp("2026-08-31 11:15:00+05:30"),"TEST",100,2);monkeypatch.setattr(runtime,"fetch_symbol_1h",lambda symbol,period="30d":candles);monkeypatch.setattr("trendpulse_runtime.trendpulse_from_frames",lambda one_h,four_h,completed_only=True:signal)
    result=runtime.scan_symbol("RELIANCE",now=pd.Timestamp("2026-08-31 12:00:00+05:30"));assert result.fresh and not result.accepted and result.reason=="READY_FOR_ACCEPTANCE";assert runtime.gate.repeat_count(signal,symbol="RELIANCE")==0
def test_runtime_accepts_fresh_signal_only_when_explicitly_requested(monkeypatch):
    runtime=TrendPulseRuntime(gate=SignalGate());candles=make_1h_frame(60);signal=StrategySignal("TrendPulse","BUY",pd.Timestamp("2026-08-31 11:15:00+05:30"),"TEST",100,2);monkeypatch.setattr(runtime,"fetch_symbol_1h",lambda symbol,period="30d":candles);monkeypatch.setattr("trendpulse_runtime.trendpulse_from_frames",lambda one_h,four_h,completed_only=True:signal)
    result=runtime.scan_symbol("RELIANCE",now=pd.Timestamp("2026-08-31 12:00:00+05:30"),accept_signal=True);assert result.accepted and result.reason=="ACCEPTED" and runtime.gate.repeat_count(signal,symbol="RELIANCE")==1
def test_runtime_rejects_stale_signal(monkeypatch):
    runtime=TrendPulseRuntime(gate=SignalGate());candles=make_1h_frame(60);signal=StrategySignal("TrendPulse","BUY",pd.Timestamp("2026-08-31 10:15:00+05:30"),"TEST",100,2);monkeypatch.setattr(runtime,"fetch_symbol_1h",lambda symbol,period="30d":candles);monkeypatch.setattr("trendpulse_runtime.trendpulse_from_frames",lambda one_h,four_h,completed_only=True:signal)
    result=runtime.scan_symbol("RELIANCE",now=pd.Timestamp("2026-08-31 12:00:01+05:30"),accept_signal=True);assert not result.accepted and result.reason=="STALE_SIGNAL"
def test_runtime_universe_is_exactly_fixed_nse15():
    from config import NSE_15_SYMBOLS
    assert len(NSE_15_SYMBOLS)==15 and len(set(NSE_15_SYMBOLS))==15
