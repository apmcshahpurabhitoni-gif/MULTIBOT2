from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from mavis.config import Settings
from mavis.domain import Candle, Freshness, Signal
from mavis.time import classify_freshness, ensure_aware

UTC = timezone.utc


def test_initial_safety_defaults_keep_live_broker_disabled():
    settings = Settings()
    assert settings.paper_trading_enabled is True
    assert settings.live_broker_enabled is False
    settings.validate_safety()


def test_live_broker_enabled_is_rejected():
    with pytest.raises(ValueError):
        Settings(live_broker_enabled=True).validate_safety()


def test_naive_datetime_is_rejected():
    with pytest.raises(ValueError):
        ensure_aware(datetime(2026, 8, 31, 10, 0))


def test_freshness_is_one_hour():
    close = datetime(2026, 8, 31, 10, 0, tzinfo=UTC)
    assert classify_freshness(close, close + timedelta(minutes=59)) is Freshness.FRESH
    assert classify_freshness(close, close + timedelta(minutes=60)) is Freshness.FRESH
    assert classify_freshness(close, close + timedelta(minutes=61)) is Freshness.STALE
    assert classify_freshness(close, close + timedelta(hours=6)) is Freshness.STALE


def test_future_close_is_rejected():
    close = datetime(2026, 8, 31, 10, 1, tzinfo=UTC)
    now = datetime(2026, 8, 31, 10, 0, tzinfo=UTC)
    with pytest.raises(ValueError):
        classify_freshness(close, now)


def test_candle_requires_timezone_aware_datetimes():
    with pytest.raises(ValueError):
        Candle(
            instrument="NIFTY",
            timeframe="1H",
            start=datetime(2026, 8, 31, 9, 15),
            end=datetime(2026, 8, 31, 10, 15),
            open=Decimal("100"), high=Decimal("110"), low=Decimal("90"), close=Decimal("105"),
            closed=True,
        )


def test_signal_enum_is_canonical():
    assert [s.value for s in Signal] == ["BUY", "SELL", "NEUTRAL", "NO_SIGNAL"]
