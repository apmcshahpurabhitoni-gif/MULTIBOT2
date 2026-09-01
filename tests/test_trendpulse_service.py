import pandas as pd

from signal_gate import SignalGate
from strategies import StrategySignal
from telegram import TelegramConfig
from trendpulse_runtime import TrendPulseRuntime, TrendPulseScanResult
from trendpulse_service import TrendPulseService


def make_signal(timestamp="2026-09-01 12:00:00+05:30"):
    return StrategySignal(
        strategy="TrendPulse",
        signal="BUY",
        timestamp=pd.Timestamp(timestamp),
        reason="TEST",
        entry=100.0,
        atr=2.0,
    )


def make_scan(signal, fresh=True):
    return TrendPulseScanResult(
        symbol="RELIANCE",
        signal=signal,
        fresh=fresh,
        accepted=False,
        reason="READY_FOR_ACCEPTANCE" if fresh else "STALE_SIGNAL",
    )


def test_service_renders_without_sending():
    now = pd.Timestamp("2026-09-01 12:30:00+05:30")
    signal = make_signal()
    runtime = TrendPulseRuntime(gate=SignalGate())
    service = TrendPulseService(
        runtime=runtime,
        telegram_config=TelegramConfig("token", "chat"),
    )

    result = service.dispatch_result(
        make_scan(signal),
        now=now,
        send=False,
    )

    assert result.sent is False
    assert result.reason == "READY_TO_SEND"
    assert result.trade is not None
    assert result.message is not None
    assert "TrendPulse · RELIANCE" in result.message.text
    assert "`₹100.00`" in result.message.text
    assert "`₹97.00`" in result.message.text
    assert "`₹106.00`" in result.message.text
    assert runtime.gate.repeat_count(signal, symbol="RELIANCE") == 0


def test_service_sends_then_records_gate(monkeypatch):
    now = pd.Timestamp("2026-09-01 12:30:00+05:30")
    signal = make_signal()
    runtime = TrendPulseRuntime(gate=SignalGate())
    service = TrendPulseService(
        runtime=runtime,
        telegram_config=TelegramConfig("token", "chat"),
    )
    sent = []

    monkeypatch.setattr(
        "trendpulse_service.send_message",
        lambda message, config: sent.append((message, config)),
    )

    result = service.dispatch_result(
        make_scan(signal),
        now=now,
        send=True,
    )

    assert result.sent is True
    assert result.reason == "SENT_AND_ACCEPTED"
    assert len(sent) == 1
    assert sent[0][0].message_type == "MSG-TRENDPULSE-BUY-V1"
    assert runtime.gate.repeat_count(signal, symbol="RELIANCE") == 1


def test_failed_telegram_send_does_not_consume_gate(monkeypatch):
    now = pd.Timestamp("2026-09-01 12:30:00+05:30")
    signal = make_signal()
    runtime = TrendPulseRuntime(gate=SignalGate())
    service = TrendPulseService(
        runtime=runtime,
        telegram_config=TelegramConfig("token", "chat"),
    )

    def fail_send(message, config):
        raise RuntimeError("temporary Telegram failure")

    monkeypatch.setattr("trendpulse_service.send_message", fail_send)

    try:
        service.dispatch_result(make_scan(signal), now=now, send=True)
    except RuntimeError as exc:
        assert str(exc) == "temporary Telegram failure"
    else:
        raise AssertionError("Telegram failure must propagate")

    assert runtime.gate.repeat_count(signal, symbol="RELIANCE") == 0


def test_stale_signal_never_sends(monkeypatch):
    now = pd.Timestamp("2026-09-01 12:30:00+05:30")
    signal = make_signal("2026-09-01 10:00:00+05:30")
    runtime = TrendPulseRuntime(gate=SignalGate())
    service = TrendPulseService(
        runtime=runtime,
        telegram_config=TelegramConfig("token", "chat"),
    )
    called = []

    monkeypatch.setattr(
        "trendpulse_service.send_message",
        lambda message, config: called.append(message),
    )

    result = service.dispatch_result(
        make_scan(signal, fresh=False),
        now=now,
        send=True,
    )

    assert result.sent is False
    assert result.reason == "STALE_SIGNAL"
    assert called == []
    assert runtime.gate.repeat_count(signal, symbol="RELIANCE") == 0
