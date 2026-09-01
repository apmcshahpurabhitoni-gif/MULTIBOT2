"""TrendPulse runtime pipeline for MULTIBOT2.

This module is the production boundary between Yahoo market data, canonical
NSE candle construction, TrendPulse evaluation, and signal gating. It does not
send Telegram messages or place trades; those actions happen only after this
pipeline returns an accepted signal.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

import pandas as pd

from config import NSE_15_SYMBOLS, IST_TIMEZONE
from market_data import build_nse_hourly_candles, yahoo_symbol
from signal_gate import SignalGate
from strategies import StrategySignal, atr, ema, trendpulse_from_frames
from yahoo_provider import YahooDataError, YahooProvider


@dataclass(frozen=True)
class TrendPulseScanResult:
    """Result of one symbol scan."""

    symbol: str
    signal: StrategySignal
    fresh: bool
    accepted: bool
    reason: str


class TrendPulseRuntime:
    """Canonical Yahoo -> candles -> TrendPulse -> gate pipeline."""

    def __init__(
        self,
        *,
        provider: YahooProvider | None = None,
        gate: SignalGate | None = None,
    ) -> None:
        self.provider = provider or YahooProvider()
        self.gate = gate or SignalGate()

    @staticmethod
    def _build_4h(frame_1h: pd.DataFrame) -> pd.DataFrame:
        """Build NSE 4H candles with the original 09:15 anchor."""
        frame_1h = frame_1h.copy()

        if frame_1h.empty:
            return frame_1h

        if frame_1h.index.tz is None:
            raise ValueError(
                "1H candle timestamps must be timezone-aware"
            )

        frame_1h.index = frame_1h.index.tz_convert(
            IST_TIMEZONE
        )

        return (
            frame_1h[["open", "high", "low", "close"]]
            .resample(
                "4h",
                origin="start_day",
                offset="9h15min",
            )
            .agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                }
            )
            .dropna()
        )

    def fetch_symbol_1h(
        self,
        symbol: str,
        *,
        period: str = "5d",
    ) -> pd.DataFrame:
        """Fetch Yahoo 1m data and construct canonical NSE 1H candles."""
        yf_symbol = yahoo_symbol(symbol)

        minute_frame = self.provider.fetch(
            yf_symbol,
            period=period,
            interval="1m",
            validate_hourly=False,
        )

        return build_nse_hourly_candles(
            minute_frame
        )

    def scan_symbol(
        self,
        symbol: str,
        *,
        now: pd.Timestamp | None = None,
        period: str = "5d",
        accept_signal: bool = False,
    ) -> TrendPulseScanResult:
        """Scan one NSE symbol through the complete TrendPulse pipeline.

        ``accept_signal`` is deliberately opt-in. Scanning never consumes a
        duplicate-send allowance unless the caller explicitly accepts it.
        """
        normalized = symbol.strip().upper()

        candles_1h = self.fetch_symbol_1h(
            normalized,
            period=period,
        )

        candles_4h = self._build_4h(
            candles_1h
        )

        signal = trendpulse_from_frames(
            candles_1h,
            candles_4h,
        )

        if signal.signal not in ("BUY", "SELL"):
            return TrendPulseScanResult(
                symbol=normalized,
                signal=signal,
                fresh=False,
                accepted=False,
                reason=signal.reason,
            )

        current = (
            pd.Timestamp.now(tz=IST_TIMEZONE)
            if now is None
            else pd.Timestamp(now)
        )

        if current.tzinfo is None:
            raise ValueError(
                "Runtime timestamp must be timezone-aware"
            )

        current = current.tz_convert(
            IST_TIMEZONE
        )

        fresh = self.gate.is_fresh(
            signal,
            now=current,
        )

        if not fresh:
            return TrendPulseScanResult(
                symbol=normalized,
                signal=signal,
                fresh=False,
                accepted=False,
                reason="STALE_SIGNAL",
            )

        if not accept_signal:
            return TrendPulseScanResult(
                symbol=normalized,
                signal=signal,
                fresh=True,
                accepted=False,
                reason="READY_FOR_ACCEPTANCE",
            )

        accepted = self.gate.accept(
            signal,
            symbol=normalized,
            now=current,
        )

        return TrendPulseScanResult(
            symbol=normalized,
            signal=signal,
            fresh=True,
            accepted=accepted,
            reason=(
                "ACCEPTED"
                if accepted
                else "DUPLICATE_SIGNAL_LIMIT"
            ),
        )

    def scan_universe(
        self,
        *,
        now: pd.Timestamp | None = None,
        period: str = "5d",
    ) -> list[TrendPulseScanResult]:
        """Scan the fixed NSE-15 universe without accepting/sending signals."""
        results: list[TrendPulseScanResult] = []

        for symbol in NSE_15_SYMBOLS:
            try:
                results.append(
                    self.scan_symbol(
                        symbol,
                        now=now,
                        period=period,
                        accept_signal=False,
                    )
                )
            except YahooDataError as exc:
                timestamp = (
                    pd.Timestamp.now(tz=IST_TIMEZONE)
                    if now is None
                    else pd.Timestamp(now).tz_convert(IST_TIMEZONE)
                )
                results.append(
                    TrendPulseScanResult(
                        symbol=symbol,
                        signal=StrategySignal(
                            strategy="TrendPulse",
                            signal="NO_SIGNAL",
                            timestamp=timestamp,
                            reason="MARKET_DATA_ERROR",
                        ),
                        fresh=False,
                        accepted=False,
                        reason=str(exc),
                    )
                )

        return results


__all__ = [
    "TrendPulseRuntime",
    "TrendPulseScanResult",
]
