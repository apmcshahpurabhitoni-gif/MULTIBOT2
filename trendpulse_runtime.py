"""Canonical 19-asset TrendPulse runtime."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from config import (
    IST_TIMEZONE,
    LIVE_ASSETS,
    LIVE_ASSET_MAP,
    AssetConfig,
)
from market_data import (
    MarketDataError,
    build_nse_hourly_candles,
)
from signal_gate import SignalGate
from strategies import (
    StrategySignal,
    derive_4h_from_1h,
    trendpulse_from_frames,
)
from yahoo_provider import (
    YahooDataError,
    YahooProvider,
)


@dataclass(frozen=True)
class TrendPulseScanResult:
    symbol: str
    signal: StrategySignal
    fresh: bool
    accepted: bool
    reason: str


class TrendPulseRuntime:

    def __init__(
        self,
        *,
        provider: YahooProvider | None = None,
        gate: SignalGate | None = None,
    ) -> None:
        self.provider = provider or YahooProvider()
        self.gate = gate or SignalGate()

    @staticmethod
    def _current(
        now: pd.Timestamp | None,
    ) -> pd.Timestamp:
        current = (
            pd.Timestamp.now(tz=IST_TIMEZONE)
            if now is None
            else pd.Timestamp(now)
        )

        if current.tzinfo is None:
            raise ValueError(
                "Runtime timestamp must be timezone-aware"
            )

        return current.tz_convert(IST_TIMEZONE)

    @staticmethod
    def _is_nse(asset: AssetConfig) -> bool:
        return asset.market == "NSE"

    def _fetch_nse_hourly(
        self,
        asset: AssetConfig,
        *,
        period: str,
    ) -> pd.DataFrame:
        minute = self.provider.fetch(
            asset.yahoo_symbol,
            period=period,
            interval="1m",
            validate_hourly=False,
        )

        return build_nse_hourly_candles(minute)

    def _fetch_global_hourly(
        self,
        asset: AssetConfig,
        *,
        period: str,
    ) -> pd.DataFrame:
        return self.provider.fetch(
            asset.yahoo_symbol,
            period=period,
            interval="1h",
            validate_hourly=False,
        )

    def fetch_symbol_1h(
        self,
        symbol: str,
        *,
        period: str = "30d",
    ) -> pd.DataFrame:
        normalized = symbol.strip().upper()

        if normalized not in LIVE_ASSET_MAP:
            raise MarketDataError(
                f"Unknown live asset: {normalized}"
            )

        asset = LIVE_ASSET_MAP[normalized]

        if self._is_nse(asset):
            return self._fetch_nse_hourly(
                asset,
                period=period,
            )

        return self._fetch_global_hourly(
            asset,
            period=period,
        )

    @staticmethod
    def _build_4h(
        frame_1h: pd.DataFrame,
    ) -> pd.DataFrame:
        return derive_4h_from_1h(frame_1h)

    def scan_symbol(
        self,
        symbol: str,
        *,
        now: pd.Timestamp | None = None,
        period: str = "30d",
        accept_signal: bool = False,
    ) -> TrendPulseScanResult:

        normalized = symbol.strip().upper()

        if normalized not in LIVE_ASSET_MAP:
            raise MarketDataError(
                f"Symbol is outside live universe: {normalized}"
            )

        current = self._current(now)
        one = self.fetch_symbol_1h(
            normalized,
            period=period,
        )

        asset = LIVE_ASSET_MAP[normalized]
        # Yahoo global 1H candles are interval-start stamped. Never evaluate
        # the currently forming bar; NSE canonical candles are close-stamped
        # by build_nse_hourly_candles and are already complete.
        if asset.market != "NSE" and not one.empty:
            complete_mask = one.index + pd.Timedelta(hours=1) <= current
            one = one.loc[complete_mask].copy()

        four = self._build_4h(one)

        signal = trendpulse_from_frames(
            one,
            four,
            completed_only=True,
        )

        if signal.signal not in ("BUY", "SELL"):
            return TrendPulseScanResult(
                normalized,
                signal,
                False,
                False,
                signal.reason,
            )

        fresh = self.gate.is_fresh(
            signal,
            now=current,
        )

        if not fresh:
            return TrendPulseScanResult(
                normalized,
                signal,
                False,
                False,
                "STALE_SIGNAL",
            )

        if not accept_signal:
            return TrendPulseScanResult(
                normalized,
                signal,
                True,
                False,
                "READY_FOR_ACCEPTANCE",
            )

        accepted = self.gate.accept(
            signal,
            symbol=normalized,
            now=current,
        )

        return TrendPulseScanResult(
            normalized,
            signal,
            True,
            accepted,
            "ACCEPTED"
            if accepted
            else "DUPLICATE_SIGNAL_LIMIT",
        )

    def scan_universe(
        self,
        *,
        now: pd.Timestamp | None = None,
        period: str = "30d",
    ) -> list[TrendPulseScanResult]:

        results: list[TrendPulseScanResult] = []

        for asset in LIVE_ASSETS:
            symbol = asset.symbol

            try:
                result = self.scan_symbol(
                    symbol,
                    now=now,
                    period=period,
                    accept_signal=False,
                )

                results.append(result)

            except (
                YahooDataError,
                MarketDataError,
                ValueError,
            ) as exc:

                current = self._current(now)

                results.append(
                    TrendPulseScanResult(
                        symbol,
                        StrategySignal(
                            "TrendPulse",
                            "NO_SIGNAL",
                            current,
                            "MARKET_DATA_ERROR",
                        ),
                        False,
                        False,
                        str(exc),
                    )
                )

        return results


__all__ = [
    "TrendPulseRuntime",
    "TrendPulseScanResult",
]
