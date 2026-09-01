"""Yahoo Finance market-data adapter for MULTIBOT2.

Yahoo is used as the market-data source, following the caching and 429
backoff approach from the original multi-strategy-telegram-bot repository.
Credentials are not required.
"""

from __future__ import annotations

import time
from threading import RLock
from typing import Optional

import pandas as pd
import requests
import yfinance as yf

from candles import validate_hourly_observations
from config import IST_TIMEZONE


YF_TTL_BY_INTERVAL = {
    "1m": 45.0,
    "1h": 300.0,
    "4h": 300.0,
    "1d": 600.0,
}
YF_SYMBOL_TTL = 45.0
YAHOO_BACKOFF_SECONDS = 600.0


class YahooDataError(RuntimeError):
    """Raised when Yahoo data cannot be safely returned."""


class YahooProvider:
    """Rate-conscious Yahoo Finance provider with per-symbol caching."""

    def __init__(self, *, session: Optional[requests.Session] = None) -> None:
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }
        )
        self._cache: dict[tuple[str, str], tuple[pd.DataFrame, float]] = {}
        self._backoff_until = 0.0
        self._lock = RLock()

    def _ttl(self, interval: str) -> float:
        return YF_TTL_BY_INTERVAL.get(interval, YF_SYMBOL_TTL)

    def _cached(self, symbol: str, interval: str) -> Optional[pd.DataFrame]:
        key = (symbol, interval)
        with self._lock:
            item = self._cache.get(key)
            if item is None:
                return None
            frame, cached_at = item
            if time.monotonic() - cached_at < self._ttl(interval):
                return frame.copy()
            self._cache.pop(key, None)
            return None

    def _store(self, symbol: str, interval: str, frame: pd.DataFrame) -> pd.DataFrame:
        with self._lock:
            self._cache[(symbol, interval)] = (frame.copy(), time.monotonic())
        return frame.copy()

    def fetch(
        self,
        symbol: str,
        *,
        period: str = "5d",
        interval: str = "1h",
        validate_hourly: bool = True,
    ) -> pd.DataFrame:
        """Fetch Yahoo candles while respecting cache and rate-limit backoff."""
        cached = self._cached(symbol, interval)
        if cached is not None:
            return cached

        now = time.monotonic()
        with self._lock:
            if now < self._backoff_until:
                raise YahooDataError("Yahoo Finance is in rate-limit backoff")

        try:
            frame = yf.download(
                symbol,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,
                threads=False,
                session=self._session,
            )
        except Exception as exc:
            if "429" in str(exc) or "too many requests" in str(exc).lower():
                with self._lock:
                    self._backoff_until = time.monotonic() + YAHOO_BACKOFF_SECONDS
            raise YahooDataError(f"Yahoo request failed for {symbol}: {exc}") from exc

        if frame is None or frame.empty:
            raise YahooDataError(f"Yahoo returned no data for {symbol}")

        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(0)

        required = {"Open", "High", "Low", "Close"}
        if not required.issubset(frame.columns):
            raise YahooDataError(
                f"Yahoo response for {symbol} is missing OHLC columns"
            )

        frame = frame[["Open", "High", "Low", "Close"]].copy()
        frame.columns = [column.lower() for column in frame.columns]

        if not isinstance(frame.index, pd.DatetimeIndex):
            raise YahooDataError("Yahoo response has no DatetimeIndex")

        if frame.index.tz is None:
            frame.index = frame.index.tz_localize("UTC")

        frame.index = frame.index.tz_convert(IST_TIMEZONE)
        frame = frame.sort_index()

        if interval == "1h" and validate_hourly:
            validate_hourly_observations(frame)

        return self._store(symbol, interval, frame)

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()

    def in_backoff(self) -> bool:
        with self._lock:
            return time.monotonic() < self._backoff_until


_default_provider = YahooProvider()


def fetch_yahoo(
    symbol: str,
    *,
    period: str = "5d",
    interval: str = "1h",
    validate_hourly: bool = True,
) -> pd.DataFrame:
    return _default_provider.fetch(
        symbol,
        period=period,
        interval=interval,
        validate_hourly=validate_hourly,
    )
