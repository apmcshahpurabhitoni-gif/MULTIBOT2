from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from mavis.config import Settings
from mavis.domain import Candle, Freshness, Instrument, Signal, SignalResult
from mavis.serialization import to_jsonable
from mavis.time import classify_freshness, ensure_aware


IST = timezone(timedelta(hours=5, minutes=30))


def test_naive_datetime_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        ensure_aware(datetime(2026, 8, 31, 10, 0))


def test_freshness_boundary_is_exactly_one_hour() -> None:
    close = datetime(2026, 8, 31, 10, 0, tzinfo=IST)
    assert classify_freshness(close, close + timedelta(hours=1)) is Freshness.FRESH
    assert classify_freshness(close, close + timedelta(hours=1, seconds=1)) is Freshness.STALE


def test_six_hours_is_stale_not_a_special_state() -> None:
    close = datetime(2026, 8, 31, 10, 0, tzinfo=IST)
    assert classify_freshness(close, close + timedelta(hours=6)) is Freshness.STALE


def test_future_candle_close_rejected() -> None:
    now = datetime(2026, 8, 31, 10, 0, tzinfo=IST)
    with pytest.raises(ValueError, match="future"):
        classify_freshness(now + timedelta(seconds=1), now)


def test_candle_requires_timezone_aware_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Candle(
            instrument="NIFTY",
            timeframe="1H",
            start=datetime(2026, 8, 31, 9, 15),
            end=datetime(2026, 8, 31, 10, 15),
            open=Decimal("1"), high=Decimal("2"), low=Decimal("1"), close=Decimal("2"),
            closed=True,
        )


def test_candle_rejects_high_below_low() -> None:
    with pytest.raises(ValueError, match="high cannot be below low"):
        Candle(
            instrument="NIFTY",
            timeframe="1H",
            start=datetime(2026, 8, 31, 9, 15, tzinfo=IST),
            end=datetime(2026, 8, 31, 10, 15, tzinfo=IST),
            open=Decimal("2"), high=Decimal("1"), low=Decimal("2"), close=Decimal("2"),
            closed=True,
        )


def test_signal_result_serializes_without_object_placeholders() -> None:
    result = SignalResult(
        strategy="FOUNDATION_TEST",
        strategy_version="1",
        instrument="NIFTY",
        signal=Signal.NO_SIGNAL,
        candle_start=datetime(2026, 8, 31, 9, 15, tzinfo=IST),
        candle_close=datetime(2026, 8, 31, 10, 15, tzinfo=IST),
        confirmation_time=datetime(2026, 8, 31, 10, 16, tzinfo=IST),
        reason="test",
        freshness=Freshness.FRESH,
        data_source="fixture",
        config_version="test",
    )
    payload = to_jsonable(result)
    assert payload["signal"] == "NO_SIGNAL"
    assert payload["freshness"] == "FRESH"
    assert payload["candle_close"].endswith("+05:30")


def test_settings_safety_disables_live_broker() -> None:
    settings = Settings(live_broker_enabled=False)
    settings.validate_safety()

    with pytest.raises(ValueError, match="LIVE_BROKER_ENABLED"):
        Settings(live_broker_enabled=True).validate_safety()


def test_domain_instrument_is_immutable() -> None:
    instrument = Instrument(canonical_symbol="NIFTY", display_symbol="NIFTY 50", exchange="NSE")
    with pytest.raises(Exception):
        instrument.canonical_symbol = "BANKNIFTY"
