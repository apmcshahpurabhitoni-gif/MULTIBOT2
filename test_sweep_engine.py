
import pandas as pd

from sweep_engine import build_closed_candles, detect_sweep
from config import IST_TIMEZONE

def make_global_raw():
    idx = pd.date_range(
        "2026-09-01 01:30", periods=16, freq="30min", tz=IST_TIMEZONE
    )
    rows = []
    for i, ts in enumerate(idx):
        if i < 8:
            rows.append((100, 101, 99, 100))
        else:
            rows.append((100, 112, 88, 110))
    return pd.DataFrame(rows, columns=["open","high","low","close"], index=idx)

def test_btc_sweep_uses_0130_boundary_and_four_hours():
    raw = make_global_raw()
    bars, tf, warning = build_closed_candles(
        raw, "BTC-USD",
        now=pd.Timestamp("2026-09-01 09:30+05:30"),
    )
    assert tf == "4H"
    assert warning is None
    assert list(bars.index) == [
        pd.Timestamp("2026-09-01 01:30+05:30"),
        pd.Timestamp("2026-09-01 05:30+05:30"),
    ]

def test_two_sided_sweep_requires_both_extremes_and_final_close():
    result = detect_sweep(
        make_global_raw(),
        "BTC-USD",
        now=pd.Timestamp("2026-09-01 09:30+05:30"),
    )
    assert result is not None
    assert result.direction == "BULLISH"
    assert result.high_swept and result.low_swept
    assert result.candle_start == pd.Timestamp("2026-09-01 05:30+05:30")
    assert result.candle_end == pd.Timestamp("2026-09-01 09:30+05:30")

def test_one_sided_sweep_is_silent():
    raw = make_global_raw()
    raw.loc[raw.index[8:], "low"] = 99
    assert detect_sweep(
        raw, "BTC-USD",
        now=pd.Timestamp("2026-09-01 09:30+05:30"),
    ) is None
