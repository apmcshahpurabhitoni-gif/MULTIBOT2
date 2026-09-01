"""Production TrendPulse orchestration: scan -> gate -> paper trade -> Telegram."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock

import pandas as pd

from config import RISK_PER_TRADE_INR, IST_TIMEZONE
from signal_gate import SignalGate
from strategies import StrategySignal, calc_sl_tp
from telegram import TelegramConfig, TelegramMessage, render_signal_message, send_message
from trading import PaperTrade, TradePlan
from trendpulse_runtime import TrendPulseRuntime, TrendPulseScanResult


@dataclass(frozen=True)
class TrendPulseDispatchResult:
    """Outcome of one TrendPulse signal dispatch attempt."""

    symbol: str
    signal: StrategySignal
    scan: TrendPulseScanResult
    trade: PaperTrade | None
    message: TelegramMessage | None
    sent: bool
    reason: str


class TrendPulseService:
    """Connect the canonical TrendPulse runtime to paper trading and Telegram.

    The service never sends a signal that is stale, outside BUY/SELL, or
    rejected by SignalGate. Telegram delivery is performed before the gate
    counter is incremented, under a lock, so a transient send failure can be
    retried without consuming a repeat allowance.
    """

    def __init__(
        self,
        *,
        runtime: TrendPulseRuntime | None = None,
        telegram_config: TelegramConfig | None = None,
    ) -> None:
        self.runtime = runtime or TrendPulseRuntime()
        self.telegram_config = telegram_config
        self._dispatch_lock = RLock()

    @staticmethod
    def _quantity(plan: TradePlan) -> float:
        """Size one paper trade to the frozen ₹2,000 risk budget."""
        risk_per_unit = plan.risk_per_unit
        if risk_per_unit <= 0:
            raise ValueError("Trade risk per unit must be positive")
        return RISK_PER_TRADE_INR / risk_per_unit

    @staticmethod
    def _now(now: pd.Timestamp | None) -> pd.Timestamp:
        current = pd.Timestamp.now(tz=IST_TIMEZONE) if now is None else pd.Timestamp(now)
        if current.tzinfo is None:
            raise ValueError("Runtime timestamp must be timezone-aware")
        return current.tz_convert(IST_TIMEZONE)

    def _config(self) -> TelegramConfig:
        if self.telegram_config is None:
            self.telegram_config = TelegramConfig.from_env()
        return self.telegram_config

    def dispatch_result(
        self,
        scan: TrendPulseScanResult,
        *,
        now: pd.Timestamp | None = None,
        send: bool = True,
    ) -> TrendPulseDispatchResult:
        """Turn an already-scanned result into one gated paper trade/message."""
        signal = scan.signal
        current = self._now(now)

        if signal.signal not in ("BUY", "SELL"):
            return TrendPulseDispatchResult(
                symbol=scan.symbol,
                signal=signal,
                scan=scan,
                trade=None,
                message=None,
                sent=False,
                reason="NO_DIRECTIONAL_SIGNAL",
            )

        if not scan.fresh:
            return TrendPulseDispatchResult(
                symbol=scan.symbol,
                signal=signal,
                scan=scan,
                trade=None,
                message=None,
                sent=False,
                reason="STALE_SIGNAL",
            )

        if not self.runtime.gate.can_send(
            signal,
            symbol=scan.symbol,
            now=current,
        ):
            return TrendPulseDispatchResult(
                symbol=scan.symbol,
                signal=signal,
                scan=scan,
                trade=None,
                message=None,
                sent=False,
                reason="DUPLICATE_SIGNAL_LIMIT",
            )

        stop_loss, take_profit = calc_sl_tp(signal)
        entry = float(signal.entry)
        plan = TradePlan(
            strategy=signal.strategy,
            side=signal.signal,
            signal_timestamp=signal.timestamp,
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        trade = PaperTrade(plan=plan)
        quantity = self._quantity(plan)

        age_hours = self.runtime.gate.age_hours(signal, now=current)
        freshness = "FRESH" if age_hours <= self.runtime.gate.max_age_hours else "STALE"
        age_minutes = int(age_hours * 60)
        age_str = (
            f"{age_minutes} min ago"
            if age_minutes < 60
            else f"{age_minutes // 60} hr {age_minutes % 60} min ago"
        )

        message = render_signal_message(
            signal,
            symbol=f"{scan.symbol}.NS",
            asset=scan.symbol.replace(".NS", ""),
            market="NSE",
            timeframe="1H",
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            quantity=quantity,
            risk=RISK_PER_TRADE_INR,
            account="nifty",
            freshness=freshness,
            age_str=age_str,
        )

        if not send:
            return TrendPulseDispatchResult(
                symbol=scan.symbol,
                signal=signal,
                scan=scan,
                trade=trade,
                message=message,
                sent=False,
                reason="READY_TO_SEND",
            )

        with self._dispatch_lock:
            if not self.runtime.gate.can_send(
                signal,
                symbol=scan.symbol,
                now=current,
            ):
                return TrendPulseDispatchResult(
                    symbol=scan.symbol,
                    signal=signal,
                    scan=scan,
                    trade=None,
                    message=None,
                    sent=False,
                    reason="DUPLICATE_SIGNAL_LIMIT",
                )

            send_message(message, self._config())

            accepted = self.runtime.gate.accept(
                signal,
                symbol=scan.symbol,
                now=current,
            )

            if not accepted:
                raise RuntimeError("Signal gate rejected a signal after successful Telegram delivery")

        return TrendPulseDispatchResult(
            symbol=scan.symbol,
            signal=signal,
            scan=scan,
            trade=trade,
            message=message,
            sent=True,
            reason="SENT_AND_ACCEPTED",
        )

    def scan_and_dispatch(
        self,
        symbol: str,
        *,
        now: pd.Timestamp | None = None,
        period: str = "5d",
        send: bool = True,
    ) -> TrendPulseDispatchResult:
        """Scan one symbol and dispatch only an approved fresh signal."""
        scan = self.runtime.scan_symbol(
            symbol,
            now=now,
            period=period,
            accept_signal=False,
        )
        return self.dispatch_result(scan, now=now, send=send)

    def scan_universe_and_dispatch(
        self,
        *,
        now: pd.Timestamp | None = None,
        period: str = "5d",
        send: bool = True,
    ) -> list[TrendPulseDispatchResult]:
        """Scan all frozen NSE-15 symbols and dispatch eligible signals."""
        scans = self.runtime.scan_universe(now=now, period=period)
        return [
            self.dispatch_result(scan, now=now, send=send)
            for scan in scans
        ]


__all__ = [
    "TrendPulseDispatchResult",
    "TrendPulseService",
]
