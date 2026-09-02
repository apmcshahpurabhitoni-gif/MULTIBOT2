import pandas as pd

from strategies import (
    calc_sl_tp,
    derive_4h_from_1h,
    trendpulse_from_frames,
)


def make_1h_frame(rows=56):
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


def test_derive_4h_from_1h():
    frame = make_1h_frame(60)
    result = derive_4h_from_1h(frame)

    assert not result.empty
    assert list(result.columns) == [
        "open",
        "high",
        "low",
        "close",
    ]


def test_trendpulse_requires_approved_history():
    frame = make_1h_frame(10)

    result = trendpulse_from_frames(frame)

    assert result.signal == "NO_SIGNAL"
    assert result.reason == "INSUFFICIENT_DATA"


def test_trendpulse_sl_tp_buy():
    from strategies import StrategySignal

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

    sl, tp = calc_sl_tp(signal)

    assert sl == 97.0
    assert tp == 106.0


def test_trendpulse_sl_tp_sell():
    from strategies import StrategySignal

    signal = StrategySignal(
        strategy="TrendPulse",
        signal="SELL",
        timestamp=pd.Timestamp(
            "2026-08-31 10:15:00+05:30"
        ),
        reason="TEST",
        entry=100.0,
        atr=2.0,
    )

    sl, tp = calc_sl_tp(signal)

    assert sl == 103.0
    assert tp == 94.0
