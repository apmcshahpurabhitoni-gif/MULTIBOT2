from __future__ import annotations

from datetime import datetime, timedelta

from mavis.domain import Freshness

FRESHNESS_LIMIT = timedelta(minutes=60)


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value


def classify_freshness(candle_close: datetime, now: datetime) -> Freshness:
    candle_close = ensure_aware(candle_close)
    now = ensure_aware(now)
    age = now - candle_close
    if age < timedelta(0):
        raise ValueError("candle_close cannot be in the future")
    return Freshness.FRESH if age <= FRESHNESS_LIMIT else Freshness.STALE
