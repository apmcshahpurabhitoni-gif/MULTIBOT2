"""Zerodha Kite Connect market-data provider for MULTIBOT2.

The fixed NSE-15 universe remains owned by config.py.
Zerodha is used only as the market-data source.

The provider deliberately fetches 1-minute candles and builds the
MULTIBOT2 1H candles itself so the project controls the exact
09:15-10:14, 10:15-11:14, ... convention instead of inheriting a
provider-specific hourly alignment.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
from datetime import date, datetime, time, timedelta
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from candles import HOURLY_OBSERVATION_TIMES
from config import (
    IST_TIMEZONE,
    NSE_15_SYMBOLS,
    settings,
)
from market_data import (
    MarketDataError,
    candles_from_records,
    validate_symbol,
)


KITE_API_ROOT = "https://api.kite.trade"


class ZerodhaProviderError(RuntimeError):
    """Raised when Zerodha market data cannot be retrieved."""


class ZerodhaProvider:
    """Minimal read-only Zerodha market-data client."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        access_token: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.zerodha_api_key
        self.access_token = access_token or settings.zerodha_access_token

        if not self.api_key:
            raise ZerodhaProviderError(
                "ZERODHA_API_KEY is not configured"
            )

        if not self.access_token:
            raise ZerodhaProviderError(
                "ZERODHA_ACCESS_TOKEN is not configured"
            )

        self._instrument_tokens: dict[str, int] | None = None

    @property
    def authorization(self) -> str:
        return f"token {self.api_key}:{self.access_token}"

    def _request_bytes(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> bytes:
        url = f"{KITE_API_ROOT}{path}"

        if params:
            url += "?" + urlencode(params)

        request = Request(
            url,
            method="GET",
            headers={
                "X-Kite-Version": "3",
                "Authorization": self.authorization,
                "Accept": "application/json",
            },
        )

        try:
            with urlopen(request, timeout=20) as response:
                return response.read()
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ZerodhaProviderError(
                f"Zerodha HTTP {exc.code}: {body[:500]}"
            ) from exc
        except URLError as exc:
            raise ZerodhaProviderError(
                f"Zerodha network error: {exc.reason}"
            ) from exc

    def _request_json(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> dict:
        raw = self._request_bytes(path, params=params)

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ZerodhaProviderError(
                "Zerodha returned invalid JSON"
            ) from exc

        if payload.get("status") != "success":
            raise ZerodhaProviderError(
                f"Zerodha request failed: {payload}"
            )

        return payload

    def load_nse_instrument_tokens(self) -> dict[str, int]:
        """Load today's NSE instrument master and keep only NSE-15 EQ rows."""
        raw = self._request_bytes("/instruments/NSE")

        try:
            try:
                decoded = gzip.decompress(raw).decode("utf-8")
            except gzip.BadGzipFile:
                decoded = raw.decode("utf-8")

            rows = csv.DictReader(io.StringIO(decoded))

            mapping: dict[str, int] = {}

            for row in rows:
                symbol = str(row.get("tradingsymbol", "")).strip().upper()

                if symbol not in NSE_15_SYMBOLS:
                    continue

                if row.get("instrument_type") != "EQ":
                    continue

                if row.get("exchange") != "NSE":
                    continue

                mapping[symbol] = int(row["instrument_token"])

        except (ValueError, KeyError, UnicodeDecodeError) as exc:
            raise ZerodhaProviderError(
                "Unable to parse Zerodha NSE instrument master"
            ) from exc

        missing = [
            symbol
            for symbol in NSE_15_SYMBOLS
            if symbol not in mapping
        ]

        if missing:
            raise ZerodhaProviderError(
                "Missing NSE-15 instrument token(s): "
                + ", ".join(missing)
            )

        self._instrument_tokens = mapping
        return dict(mapping)

    def instrument_token(self, symbol: str) -> int:
        symbol = validate_symbol(symbol)

        if symbol not in NSE_15_SYMBOLS:
            raise ZerodhaProviderError(
                f"Symbol is outside the fixed NSE-15 universe: {symbol}"
            )

        if self._instrument_tokens is None:
            self.load_nse_instrument_tokens()

        assert self._instrument_tokens is not None
        return self._instrument_tokens[symbol]

    @staticmethod
    def _date_bounds(day: date) -> tuple[str, str]:
        start = datetime.combine(day, time(9, 15))
        end = datetime.combine(day, time(15, 30))
        return (
            start.strftime("%Y-%m-%d %H:%M:%S"),
            end.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def fetch_minute_candles(
        self,
        symbol: str,
        *,
        trading_day: date,
    ) -> pd.DataFrame:
        """Fetch one NSE trading day's 1-minute candles."""
        token = self.instrument_token(symbol)
        start, end = self._date_bounds(trading_day)

        payload = self._request_json(
            f"/instruments/historical/{token}/minute",
            params={
                "from": start,
                "to": end,
            },
        )

        candles = payload.get("data", {}).get("candles", [])

        records = []
        for row in candles:
            if len(row) < 6:
                raise ZerodhaProviderError(
                    "Unexpected Zerodha candle record"
                )

            records.append(
                {
                    "timestamp": row[0],
                    "open": row[1],
                    "high": row[2],
                    "low": row[3],
                    "close": row[4],
                    "volume": row[5],
                }
            )

        return candles_from_records(records)

    @staticmethod
    def aggregate_nse_1h(
        minute_frame: pd.DataFrame,
    ) -> pd.DataFrame:
        """Build exact MULTIBOT2 1H candles from 1-minute data.

        Each complete candle contains exactly 60 minute observations:

            09:15-10:14 -> timestamp 10:15
            10:15-11:14 -> timestamp 11:15
            ...
            14:15-15:14 -> timestamp 15:15

        Incomplete windows are omitted rather than guessed.
        """
        if minute_frame.empty:
            return pd.DataFrame(
                columns=[
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ],
                index=pd.DatetimeIndex([], tz=IST_TIMEZONE),
            )

        frame = minute_frame.copy()
        frame.index = pd.to_datetime(frame.index)

        if frame.index.tz is None:
            raise MarketDataError(
                "Minute candles must be timezone-aware"
            )

        frame.index = frame.index.tz_convert(IST_TIMEZONE)
        frame = frame.sort_index()

        rows: list[dict[str, object]] = []

        for day, day_frame in frame.groupby(frame.index.date):
            day_start = pd.Timestamp(
                datetime.combine(day, time(9, 15)),
                tz=IST_TIMEZONE,
            )

            session_end = pd.Timestamp(
                datetime.combine(day, time(15, 15)),
                tz=IST_TIMEZONE,
            )

            session = day_frame.loc[
                (day_frame.index >= day_start)
                & (day_frame.index < session_end)
            ]

            for close_time in HOURLY_OBSERVATION_TIMES:
                close = pd.Timestamp(
                    datetime.combine(day, close_time),
                    tz=IST_TIMEZONE,
                )
                start = close - pd.Timedelta(hours=1)

                window = session.loc[
                    (session.index >= start)
                    & (session.index < close)
                ]

                if len(window) != 60:
                    continue

                expected = pd.date_range(
                    start=start,
                    periods=60,
                    freq="min",
                    tz=IST_TIMEZONE,
                )

                if not window.index.equals(expected):
                    continue

                row: dict[str, object] = {
                    "timestamp": close,
                    "open": float(window["open"].iloc[0]),
                    "high": float(window["high"].max()),
                    "low": float(window["low"].min()),
                    "close": float(window["close"].iloc[-1]),
                }

                if "volume" in window.columns:
                    row["volume"] = float(window["volume"].sum())

                rows.append(row)

        return candles_from_records(rows)

    def fetch_1h_candles(
        self,
        symbol: str,
        *,
        trading_day: date,
    ) -> pd.DataFrame:
        """Fetch and construct canonical MULTIBOT2 1H candles."""
        minute = self.fetch_minute_candles(
            symbol,
            trading_day=trading_day,
        )

        return self.aggregate_nse_1h(minute)
