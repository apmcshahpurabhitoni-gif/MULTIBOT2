import pandas as pd
import pytest

from signal_gate import (
    MAX_MESSAGE_SEND_COUNT,
    SignalGate,
    signal_status,
)
from strategies import StrategySignal


def make_signal(
    timestamp="2026-08-31 10:15:00+05:30",
    signal="BUY",
):
    return StrategySignal(
        strategy="TrendPulse",
        signal=signal,
        timestamp=pd.Timestamp(timestamp),
        reason="TEST",
        entry=100.0,
        atr=2.0,
    )


def test_fresh_signal_is_accepted():
    gate = SignalGate()

    signal = make_signal()

    now = pd.Timestamp(
        "2026-08-31 11:15:00+05:30"
    )

    assert gate.is_fresh(
        signal,
        now=now,
    )

    assert gate.can_send(
        signal,
        symbol="RELIANCE",
        now=now,
    )


def test_exactly_one_hour_is_fresh():
    gate = SignalGate()

    signal = make_signal()

    now = pd.Timestamp(
        "2026-08-31 11:15:00+05:30"
    )

    assert gate.age_hours(
        signal,
        now=now,
    ) == 1.0

    assert gate.is_fresh(
        signal,
        now=now,
    )


def test_signal_older_than_one_hour_is_stale():
    gate = SignalGate()

    signal = make_signal()

    now = pd.Timestamp(
        "2026-08-31 11:15:01+05:30"
    )

    assert not gate.is_fresh(
        signal,
        now=now,
    )

    assert not gate.can_send(
        signal,
        symbol="RELIANCE",
        now=now,
    )


def test_future_signal_is_rejected():
    gate = SignalGate()

    signal = make_signal(
        "2026-08-31 12:15:00+05:30"
    )

    now = pd.Timestamp(
        "2026-08-31 11:15:00+05:30"
    )

    with pytest.raises(ValueError):
        gate.is_fresh(
            signal,
            now=now,
        )


def test_first_and_second_identical_send_are_allowed():
    gate = SignalGate()

    signal = make_signal()

    now = pd.Timestamp(
        "2026-08-31 11:00:00+05:30"
    )

    assert gate.accept(
        signal,
        symbol="RELIANCE",
        now=now,
    )

    assert gate.accept(
        signal,
        symbol="RELIANCE",
        now=now,
    )


def test_third_identical_send_is_blocked():
    gate = SignalGate()

    signal = make_signal()

    now = pd.Timestamp(
        "2026-08-31 11:00:00+05:30"
    )

    assert gate.accept(
        signal,
        symbol="RELIANCE",
        now=now,
    )

    assert gate.accept(
        signal,
        symbol="RELIANCE",
        now=now,
    )

    assert not gate.accept(
        signal,
        symbol="RELIANCE",
        now=now,
    )


def test_repeat_limit_is_two():
    assert MAX_MESSAGE_SEND_COUNT == 2


def test_new_candle_timestamp_is_new_signal():
    gate = SignalGate()

    first = make_signal(
        "2026-08-31 10:15:00+05:30"
    )

    second = make_signal(
        "2026-08-31 11:15:00+05:30"
    )

    now = pd.Timestamp(
        "2026-08-31 12:00:00+05:30"
    )

    assert gate.accept(
        first,
        symbol="RELIANCE",
        now=now,
    )

    assert gate.accept(
        second,
        symbol="RELIANCE",
        now=now,
    )


def test_different_symbol_is_new_signal():
    gate = SignalGate()

    signal = make_signal()

    now = pd.Timestamp(
        "2026-08-31 11:00:00+05:30"
    )

    assert gate.accept(
        signal,
        symbol="RELIANCE",
        now=now,
    )

    assert gate.accept(
        signal,
        symbol="TCS",
        now=now,
    )


def test_different_direction_is_new_signal():
    gate = SignalGate()

    buy = make_signal(
        signal="BUY"
    )

    sell = make_signal(
        signal="SELL"
    )

    now = pd.Timestamp(
        "2026-08-31 11:00:00+05:30"
    )

    assert gate.accept(
        buy,
        symbol="RELIANCE",
        now=now,
    )

    assert gate.accept(
        sell,
        symbol="RELIANCE",
        now=now,
    )


def test_neutral_is_supported_but_invalid_no_signal_is_not():
    gate = SignalGate()

    neutral = make_signal(
        signal="NEUTRAL"
    )

    no_signal = make_signal(
        signal="NO_SIGNAL"
    )

    now = pd.Timestamp(
        "2026-08-31 11:00:00+05:30"
    )

    assert gate.accept(
        neutral,
        symbol="RELIANCE",
        now=now,
    )

    assert not gate.accept(
        no_signal,
        symbol="RELIANCE",
        now=now,
    )


def test_snapshot_and_restore():
    gate = SignalGate()

    signal = make_signal()

    now = pd.Timestamp(
        "2026-08-31 11:00:00+05:30"
    )

    assert gate.accept(
        signal,
        symbol="RELIANCE",
        now=now,
    )

    saved = gate.snapshot()

    restored = SignalGate()
    restored.restore(saved)

    assert (
        restored.repeat_count(
            signal,
            symbol="RELIANCE",
        )
        == 1
    )


def test_clear_removes_repeat_history():
    gate = SignalGate()

    signal = make_signal()

    now = pd.Timestamp(
        "2026-08-31 11:00:00+05:30"
    )

    assert gate.accept(
        signal,
        symbol="RELIANCE",
        now=now,
    )

    gate.clear()

    assert gate.repeat_count(
        signal,
        symbol="RELIANCE",
    ) == 0


def test_signal_status_fresh():
    signal = make_signal()

    now = pd.Timestamp(
        "2026-08-31 11:15:00+05:30"
    )

    status, age = signal_status(
        signal,
        now=now,
    )

    assert status == "FRESH"
    assert age == 1.0


def test_signal_status_stale():
    signal = make_signal()

    now = pd.Timestamp(
        "2026-08-31 12:15:01+05:30"
    )

    status, age = signal_status(
        signal,
        now=now,
    )

    assert status == "STALE"
    assert age > 1.0
