"""Canonical 19-asset Sweep V2 service."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock

import pandas as pd

from config import (
    ACCOUNT_NAMES,
    ACCOUNT_SIZE_INR,
    IST_TIMEZONE,
    LIVE_ASSETS,
    LIVE_ASSET_MAP,
)
from db import DatabaseManager
from signal_gate import SignalGate
from strategies import StrategySignal
from sweep_engine import detect_sweep
from telegram import (
    TelegramConfig,
    TelegramMessage,
    render_signal_message,
    send_message,
    signal_rejection_message,
)
from trading import (
    AccountState,
    PaperTrade,
    can_open_trade,
    make_sweep_trade_plan,
    quantity_for_risk,
    register_trade,
)
from trendpulse_runtime import TrendPulseRuntime


@dataclass(frozen=True)
class SweepDispatchResult:
    symbol: str
    signal: StrategySignal
    trade: PaperTrade | None
    message: TelegramMessage | None
    sent: bool
    reason: str
    account: str = "sweep_4h"


class SweepService:

    DEFAULT_ACCOUNT = "sweep_4h"

    def __init__(
        self,
        *,
        runtime=None,
        telegram_config=None,
        database=None,
        accounts=None,
    ):
        self.runtime = (
            runtime or TrendPulseRuntime()
        )

        self.telegram_config = telegram_config
        self.database = (
            database or DatabaseManager()
        )

        self.gate = SignalGate()
        self._lock = RLock()

        if accounts is not None:
            self.accounts = accounts
        else:
            rows = self.database.load_accounts(
                ACCOUNT_NAMES,
                ACCOUNT_SIZE_INR,
                pd.Timestamp.now(
                    tz=IST_TIMEZONE
                ).date().isoformat(),
            )

            self.accounts = {
                name: AccountState(
                    name,
                    float(
                        rows[name]["starting_balance"]
                    ),
                    float(rows[name]["balance"]),
                    float(
                        rows[name]["planned_risk_used"]
                    ),
                    int(rows[name]["trades_today"]),
                )
                for name in ACCOUNT_NAMES
            }

    def _config(self):
        return (
            self.telegram_config
            or TelegramConfig.from_env()
        )

    @staticmethod
    def _now(now):
        current = (
            pd.Timestamp.now(
                tz=IST_TIMEZONE
            )
            if now is None
            else pd.Timestamp(now)
        )

        if current.tzinfo is None:
            raise ValueError(
                "Runtime timestamp must be timezone-aware"
            )

        return current.tz_convert(
            IST_TIMEZONE
        )

    def _fetch(
        self,
        asset,
        period="30d",
    ):
        return self.runtime.fetch_symbol_1h(
            asset.symbol,
            period=period,
        )

    def _price(self, asset):
        try:
            frame = self.runtime.provider.fetch(
                asset.yahoo_symbol,
                period="2d",
                interval="1m",
                validate_hourly=False,
            )

            if frame.empty:
                return None

            return float(frame.close.iloc[-1])

        except Exception:
            return None

    def _reject(
        self,
        symbol,
        signal,
        reason,
        account_name,
    ):
        return SweepDispatchResult(
            symbol,
            signal,
            None,
            signal_rejection_message(
                strategy="Sweep V2",
                symbol=symbol,
                reason=reason,
            ),
            False,
            reason,
            account_name,
        )

    def dispatch(
        self,
        asset,
        signal,
        candles_1h,
        *,
        current_price,
        now=None,
        send=True,
        account_name=DEFAULT_ACCOUNT,
    ):
        current = self._now(now)

        if signal.signal not in (
            "BUY",
            "SELL",
        ):
            return self._reject(
                asset.symbol,
                signal,
                "NO_DIRECTIONAL_SIGNAL",
                account_name,
            )

        if not self.gate.is_fresh(
            signal,
            now=current,
        ):
            return self._reject(
                asset.symbol,
                signal,
                "STALE_SIGNAL",
                account_name,
            )

        key = self.gate.signal_key(
            signal,
            symbol=asset.symbol,
        )

        with self._lock:

            count = self.database.signal_count(
                key
            )

            if count >= 2:
                return self._reject(
                    asset.symbol,
                    signal,
                    "DUPLICATE_SIGNAL_LIMIT",
                    account_name,
                )

            if count == 1:
                return self._reject(
                    asset.symbol,
                    signal,
                    "REMINDER_PENDING",
                    account_name,
                )

            account = self.accounts[
                account_name
            ]

            if not can_open_trade(account):
                return self._reject(
                    asset.symbol,
                    signal,
                    "ACCOUNT_DAILY_LIMIT",
                    account_name,
                )

            if (
                candles_1h is None
                or candles_1h.empty
            ):
                return self._reject(
                    asset.symbol,
                    signal,
                    "MISSING_SIGNAL_CANDLE",
                    account_name,
                )

            candle = candles_1h.iloc[-1]

            plan = make_sweep_trade_plan(
                signal,
                entry=float(current_price),
                signal_high=float(candle.high),
                signal_low=float(candle.low),
            )

            if plan is None:
                return self._reject(
                    asset.symbol,
                    signal,
                    "NO_DIRECTIONAL_SIGNAL",
                    account_name,
                )

            qty = quantity_for_risk(
                plan.entry,
                plan.stop_loss,
            )

            trade = PaperTrade(
                plan=plan,
                account=account_name,
                quantity=qty,
            )

            age = max(
                0,
                int(
                    (
                        current
                        - signal.timestamp
                    ).total_seconds()
                    / 60
                ),
            )

            age_text = (
                f"{age} min ago"
                if age < 60
                else (
                    f"{age // 60} hr "
                    f"{age % 60} min ago"
                )
            )

            message = render_signal_message(
                signal,
                symbol=asset.symbol,
                asset=asset.label,
                market=asset.market,
                timeframe=asset.sweep_timeframe,
                entry=plan.entry,
                stop_loss=plan.stop_loss,
                take_profit=plan.take_profit,
                quantity=qty,
                risk=trade.planned_risk,
                account=account_name,
                freshness="FRESH",
                age_str=age_text,
            )

            if not send:
                return SweepDispatchResult(
                    asset.symbol,
                    signal,
                    trade,
                    message,
                    False,
                    "READY_TO_SEND",
                    account_name,
                )

            send_message(
                message,
                self._config(),
            )

            self.database.record_signal_send(
                key,
                current.isoformat(),
                (
                    current
                    + pd.Timedelta(hours=1)
                ).isoformat(),
                message.text,
                {
                    "message_type":
                        message.message_type,
                    "strategy":
                        signal.strategy,
                    "symbol":
                        asset.symbol,
                    "direction":
                        signal.signal,
                    "timestamp":
                        signal.timestamp.isoformat(),
                    "reason":
                        signal.reason,
                },
            )

            updated = register_trade(
                account,
                planned_risk=trade.planned_risk,
            )

            self.accounts[account_name] = (
                updated
            )

            self.database.save_account(
                account_name,
                balance=updated.balance,
                trades_today=updated.trades_today,
                planned_risk_used=(
                    updated.planned_risk_used
                ),
                reset_date=(
                    current.date().isoformat()
                ),
            )

            self.gate.accept(
                signal,
                symbol=asset.symbol,
                now=current,
            )

            return SweepDispatchResult(
                asset.symbol,
                signal,
                trade,
                message,
                True,
                "SENT_AND_ACCEPTED",
                account_name,
            )

    def scan_symbol(
        self,
        symbol,
        *,
        period="30d",
        now=None,
    ):
        normalized = symbol.strip().upper()

        if normalized not in LIVE_ASSET_MAP:
            raise ValueError(
                f"Unknown live asset: {normalized}"
            )

        asset = LIVE_ASSET_MAP[
            normalized
        ]

        frame = self._fetch(
            asset,
            period,
        )

        current = self._now(now)

        result = detect_sweep(
            frame,
            asset.symbol,
            current,
        )

        timestamp = (
            result.candle_end
            if result is not None
            else (
                frame.index[-1]
                if len(frame)
                else current
            )
        )

        direction = {
            "BULLISH": "BUY",
            "BEARISH": "SELL",
            "NEUTRAL": "NEUTRAL",
        }.get(
            result.direction
            if result is not None
            else "",
            "NO_SIGNAL",
        )

        reason = (
            result.direction
            if result is not None
            else "NO_SIGNAL"
        )

        signal = StrategySignal(
            "Sweep V2",
            direction,
            timestamp,
            reason,
        )

        return signal, frame

    def scan_universe_and_dispatch(
        self,
        *,
        now=None,
        period="30d",
        send=True,
    ):
        current = self._now(now)

        output = []

        for asset in LIVE_ASSETS:

            try:
                signal, frame = (
                    self.scan_symbol(
                        asset.symbol,
                        period=period,
                        now=current,
                    )
                )

                if signal.signal not in (
                    "BUY",
                    "SELL",
                ):
                    continue

                price = self._price(asset)

                if price is None:
                    continue

                result = self.dispatch(
                    asset,
                    signal,
                    frame,
                    current_price=price,
                    now=current,
                    send=send,
                    account_name=self.DEFAULT_ACCOUNT,
                )

                output.append(result)

            except Exception:
                # One broken provider/asset must not
                # stop the remaining 18 assets.
                continue

        return output

    def start(self, *_, **__):
        return None

    def stop(self):
        return None


__all__ = [
    "SweepDispatchResult",
    "SweepService",
]
