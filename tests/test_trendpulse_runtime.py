import pandas as pd

from signal_gate import SignalGate
from strategies import StrategySignal
from trendpulse_runtime import TrendPulseRuntime


def make_1h_frame(rows=60):
    index = pd.date_range(
        "2026-08-31 09:15:00+05:30",
        periods=rows,
        freq="1h",
    )
    close = pd.Series(
        [100.0 + i for i in range(rows)],
        index=index,
    )
    return pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
        },
        index=index,
    )


def test_runtime_uses_0915_anchored_4h_buckets():
    frame = make_1h_frame(60)
    result = TrendPulseRuntime._build_4h(frame)

    assert not result.empty
    assert result.index[0] == pd.Timestamp(
        "2026-08-31 09:15:00+05:30"
    )


def test_runtime_4h_buckets_are_four_hours_apart():
    frame = make_1h_frame(60)
    result = TrendPulseRuntime._build_4h(frame)

    differences = result.index.to_series().diff().dropna()

    assert all(difference == pd.Timedelta(hours=4) for difference in differences)


def test_runtime_scan_does_not_consume_gate_by_default(monkeypatch):
    runtime = TrendPulseRuntime(gate=SignalGate())

    candles_1h = make_1h_frame(60)
    candles_4h = runtime._build_4h(candles_1h)

    signal = StrategySignal(
        strategy="TrendPulse",
        signal="BUY",
        timestamp=pd.Timestamp(
            "2026-08-31 11:15:00+05:30"
        ),
        reason="TEST",
        entry=100.0,
        atr=2.0,
    )

    monkeypatch.setattr(
        runtime,
        "fetch_symbol_1h",
        lambda symbol, period="5d": candles_1h,
    )

    monkeypatch.setattr(
        "trendpulse_runtime.trendpulse_from_frames",
        lambda one_h, four_h: signal,
    )

    result = runtime.scan_symbol(
        "RELIANCE",
        now=pd.Timestamp(
            "2026-08-31 12:00:00+05:30"
        ),
    )

    assert result.fresh is True
    assert result.accepted is False
    assert result.reason == "READY_FOR_ACCEPTANCE"
    assert runtime.gate.repeat_count(
        signal,
        symbol="RELIANCE",
    ) == 0


def test_runtime_accepts_fresh_signal_only_when_explicitly_requested(monkeypatch):
    runtime = TrendPulseRuntime(gate=SignalGate())

    candles_1h = make_1h_frame(60)

    signal = StrategySignal(
        strategy="TrendPulse",
        signal="BUY",
        timestamp=pd.Timestamp(
            "2026-08-31 11:15:00+05:30"
        ),
        reason="TEST",
        entry=100.0,
        atr=2.0,
    )

    monkeypatch.setattr(
        runtime,
        "fetch_symbol_1h",
        lambda symbol, period="5d": candles_1h,
    )
    monkeypatch.setattr(
        "trendpulse_runtime.trendpulse_from_frames",
        lambda one_h, four_h: signal,
    )

    result = runtime.scan_symbol(
        "RELIANCE",
        now=pd.Timestamp(
            "2026-08-31 12:00:00+05:30"
        ),
        accept_signal=True,
    )

    assert result.accepted is True
    assert result.reason == "ACCEPTED"
    assert runtime.gate.repeat_count(
        signal,
        symbol="RELIANCE",
    ) == 1


def test_runtime_rejects_stale_signal(monkeypatch):
    runtime = TrendPulseRuntime(gate=SignalGate())

    candles_1h = make_1h_frame(60)

    signal = StrategySignal(
        strategy="TrendPulse",
        signal="BUY",
        timestamp=pd.Timestamp(
            "2026-08-31 10:15:00+05:30"
        ),
        reason="TEST",
        entry=100.0,
        atr=2.0,
    )

    monkeypatch.setattr(
        runtime,
        "fetch_symbol_1h",
        lambda symbol, period="5d": candles_1h,
    )
    monkeypatch.setattr(
        "trendpulse_runtime.trendpulse_from_frames",
        lambda one_h, four_h: signal,
    )

    result = runtime.scan_symbol(
        "RELIANCE",
        now=pd.Timestamp(
            "2026-08-31 12:00:01+05:30"
        ),
        accept_signal=True,
    )

    assert result.accepted is False
    assert result.reason == "STALE_SIGNAL"


def test_runtime_universe_is_exactly_fixed_nse15():
    from config import NSE_15_SYMBOLS

    assert len(NSE_15_SYMBOLS) == 15
    assert len(set(NSE_15_SYMBOLS)) == 15
