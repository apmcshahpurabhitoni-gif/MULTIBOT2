from datetime import datetime, date, time

import pandas as pd
import pytest

from zerodha_provider import (
    ZerodhaProvider,
    ZerodhaProviderError,
)


IST = "Asia/Kolkata"


def make_minute_frame(
    start: str,
    periods: int,
) -> pd.DataFrame:
    index = pd.date_range(
        start=start,
        periods=periods,
        freq="min",
        tz=IST,
    )

    base = pd.Series(
        range(100, 100 + periods),
        index=index,
        dtype=float,
    )

    return pd.DataFrame(
        {
            "open": base,
            "high": base + 2,
            "low": base - 1,
            "close": base + 1,
            "volume": 10,
        },
        index=index,
    )


def test_aggregate_first_hour_is_0915_to_1014():
    frame = make_minute_frame(
        "2026-09-01 09:15:00+05:30",
        60,
    )

    result = ZerodhaProvider.aggregate_nse_1h(frame)

    assert list(result.index) == [
        pd.Timestamp("2026-09-01 10:15:00+05:30")
    ]

    candle = result.iloc[0]

    assert candle["open"] == 100
    assert candle["close"] == 160
    assert candle["high"] == 161
    assert candle["low"] == 99
    assert candle["volume"] == 600


def test_aggregate_second_hour_is_1015_to_1114():
    frame = make_minute_frame(
        "2026-09-01 10:15:00+05:30",
        60,
    )

    result = ZerodhaProvider.aggregate_nse_1h(frame)

    assert list(result.index) == [
        pd.Timestamp("2026-09-01 11:15:00+05:30")
    ]


def test_incomplete_hour_is_not_guessed():
    frame = make_minute_frame(
        "2026-09-01 09:15:00+05:30",
        59,
    )

    result = ZerodhaProvider.aggregate_nse_1h(frame)

    assert result.empty


def test_missing_minute_is_not_guessed():
    frame = make_minute_frame(
        "2026-09-01 09:15:00+05:30",
        60,
    ).drop(
        pd.Timestamp("2026-09-01 09:30:00+05:30")
    )

    result = ZerodhaProvider.aggregate_nse_1h(frame)

    assert result.empty


def test_final_hour_closes_at_1515():
    frame = make_minute_frame(
        "2026-09-01 14:15:00+05:30",
        60,
    )

    result = ZerodhaProvider.aggregate_nse_1h(frame)

    assert list(result.index) == [
        pd.Timestamp("2026-09-01 15:15:00+05:30")
    ]


def test_1516_to_1530_is_not_an_hourly_candle():
    frame = make_minute_frame(
        "2026-09-01 15:15:00+05:30",
        16,
    )

    result = ZerodhaProvider.aggregate_nse_1h(frame)

    assert result.empty


def test_symbol_outside_fixed_universe_is_rejected():
    provider = object.__new__(ZerodhaProvider)
    provider.api_key = "test"
    provider.access_token = "test"
    provider._instrument_tokens = {
        "RELIANCE": 1,
    }

    with pytest.raises(ZerodhaProviderError):
        provider.instrument_token("AAPL")


def test_provider_requires_credentials(monkeypatch):
    monkeypatch.delenv("ZERODHA_API_KEY", raising=False)
    monkeypatch.delenv("ZERODHA_ACCESS_TOKEN", raising=False)

    with pytest.raises(ZerodhaProviderError):
        ZerodhaProvider(
            api_key=None,
            access_token=None,
        )
