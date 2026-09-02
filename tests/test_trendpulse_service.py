import pandas as pd
from db import DatabaseManager
from signal_gate import SignalGate
from strategies import StrategySignal
from telegram import TelegramConfig
from trendpulse_runtime import TrendPulseRuntime,TrendPulseScanResult
from trendpulse_service import TrendPulseService

def make_signal(timestamp="2026-09-01 12:00:00+05:30"):
    return StrategySignal("TrendPulse","BUY",pd.Timestamp(timestamp),"TEST",100.0,2.0)
def make_scan(signal,fresh=True):return TrendPulseScanResult("RELIANCE",signal,fresh,False,"READY_FOR_ACCEPTANCE" if fresh else "STALE_SIGNAL")
def make_service(tmp_path):
    runtime=TrendPulseRuntime(gate=SignalGate());db=DatabaseManager(str(tmp_path/"state.db"));service=TrendPulseService(runtime=runtime,telegram_config=TelegramConfig("token","chat"),database=db);return runtime,service

def test_service_renders_without_sending(tmp_path):
    runtime,service=make_service(tmp_path);signal=make_signal();result=service.dispatch_result(make_scan(signal),now=pd.Timestamp("2026-09-01 12:30:00+05:30"),send=False)
    assert not result.sent and result.reason=="READY_TO_SEND" and result.trade is not None and result.message is not None
    assert "TrendPulse · RELIANCE" in result.message.text and "`₹100.00`" in result.message.text and "`₹97.00`" in result.message.text and "`₹106.00`" in result.message.text
    assert runtime.gate.repeat_count(signal,symbol="RELIANCE")==0

def test_service_sends_then_records_gate(tmp_path,monkeypatch):
    runtime,service=make_service(tmp_path);signal=make_signal();sent=[];monkeypatch.setattr("trendpulse_service.send_message",lambda message,config:sent.append((message,config)))
    result=service.dispatch_result(make_scan(signal),now=pd.Timestamp("2026-09-01 12:30:00+05:30"),send=True)
    assert result.sent and result.reason=="SENT_AND_ACCEPTED" and len(sent)==1 and sent[0][0].message_type=="MSG-TRENDPULSE-BUY-V1" and runtime.gate.repeat_count(signal,symbol="RELIANCE")==1

def test_failed_telegram_send_does_not_consume_gate(tmp_path,monkeypatch):
    runtime,service=make_service(tmp_path);signal=make_signal()
    monkeypatch.setattr("trendpulse_service.send_message",lambda message,config:(_ for _ in ()).throw(RuntimeError("temporary Telegram failure")))
    try:service.dispatch_result(make_scan(signal),now=pd.Timestamp("2026-09-01 12:30:00+05:30"),send=True)
    except RuntimeError as exc:assert str(exc)=="temporary Telegram failure"
    else:raise AssertionError("Telegram failure must propagate")
    assert runtime.gate.repeat_count(signal,symbol="RELIANCE")==0

def test_stale_signal_never_sends(tmp_path,monkeypatch):
    runtime,service=make_service(tmp_path);signal=make_signal("2026-09-01 10:00:00+05:30");called=[];monkeypatch.setattr("trendpulse_service.send_message",lambda message,config:called.append(message))
    result=service.dispatch_result(make_scan(signal,False),now=pd.Timestamp("2026-09-01 12:30:00+05:30"),send=True)
    assert not result.sent and result.reason=="STALE_SIGNAL" and called==[] and runtime.gate.repeat_count(signal,symbol="RELIANCE")==0

def test_non_directional_scan_is_silent(tmp_path,monkeypatch):
    runtime,service=make_service(tmp_path)
    signal=StrategySignal("TrendPulse","NEUTRAL",pd.Timestamp("2026-09-01 12:00:00+05:30"),"NO_SETUP",100.0,2.0)
    sent=[];monkeypatch.setattr("trendpulse_service.send_message",lambda message,config:sent.append(message))
    result=service.dispatch_result(make_scan(signal),now=pd.Timestamp("2026-09-01 12:30:00+05:30"),send=True)
    assert not result.sent and result.reason=="NO_DIRECTIONAL_SIGNAL" and result.message is None and sent==[]

def test_rejection_diagnostics_never_send_to_telegram(tmp_path,monkeypatch):
    runtime,service=make_service(tmp_path);sent=[]
    monkeypatch.setattr("trendpulse_service.send_message",lambda message,config:sent.append(message))
    stale=make_signal("2026-09-01 10:00:00+05:30")
    result=service.dispatch_result(make_scan(stale,False),now=pd.Timestamp("2026-09-01 12:30:00+05:30"),send=True)
    assert result.reason=="STALE_SIGNAL" and not result.sent and result.message is not None and sent==[]
