"""Complete Sweep V2 runtime and dispatch service."""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock

import pandas as pd

from config import ACCOUNT_SIZE_INR, ACCOUNT_NAMES, IST_TIMEZONE, NSE_15_SYMBOLS, RISK_PER_TRADE_INR
from db import DatabaseManager
from market_data import MarketDataError
from signal_gate import SignalGate
from strategies import StrategySignal, sweep_v2_from_frame
from telegram import TelegramConfig, TelegramMessage, render_signal_message, send_message, signal_rejection_message
from trading import AccountState, PaperTrade, TradePlan, can_open_trade, register_trade
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

    def __init__(self, *, runtime=None, telegram_config=None, database=None, accounts=None):
        self.runtime = runtime or TrendPulseRuntime()
        self.telegram_config = telegram_config
        self.database = database or DatabaseManager()
        self.gate = SignalGate()
        self._lock = RLock()
        if accounts is not None:
            self.accounts = accounts
        else:
            rows = self.database.load_accounts(
                ACCOUNT_NAMES,
                ACCOUNT_SIZE_INR,
                pd.Timestamp.now(tz=IST_TIMEZONE).date().isoformat(),
            )
            self.accounts = {
                n: AccountState(
                    n,
                    float(rows[n]["starting_balance"]),
                    float(rows[n]["balance"]),
                    float(rows[n]["planned_risk_used"]),
                    int(rows[n]["trades_today"]),
                )
                for n in ACCOUNT_NAMES
            }

    def _config(self):
        return self.telegram_config or TelegramConfig.from_env()

    def _reject(self, symbol, signal, reason, *, send=True, account_name=DEFAULT_ACCOUNT, detail=""):
        message = signal_rejection_message(
            strategy=getattr(signal, "strategy", "Sweep V2"),
            symbol=symbol,
            reason=reason,
            detail=detail,
        )
        if send:
            try:
                send_message(message, self._config())
            except Exception:
                pass
        return SweepDispatchResult(symbol, signal, None, message if send else None, False, reason, account_name)

    def scan_symbol(self, symbol, *, period="30d"):
        normalized = symbol.strip().upper()
        if normalized not in NSE_15_SYMBOLS:
            raise MarketDataError(f"Symbol is outside fixed NSE-15 universe: {normalized}")
        # LOCKED RULE: NSE market data and user-facing strategy timeframe are 1H.
        one_hour = self.runtime.fetch_symbol_1h(normalized, period=period)
        return sweep_v2_from_frame(one_hour), one_hour

    def dispatch(self, symbol, signal, candles_1h, *, current_price, now=None, send=True, account_name=DEFAULT_ACCOUNT):
        current = pd.Timestamp.now(tz=IST_TIMEZONE) if now is None else pd.Timestamp(now)
        if current.tzinfo is None:
            raise ValueError("Current timestamp must be timezone-aware")
        current = current.tz_convert(IST_TIMEZONE)
        account = self.accounts.get(account_name)
        if account is None:
            raise ValueError(f"Unknown account: {account_name}")

        if signal.signal not in ("BUY", "SELL"):
            return self._reject(symbol, signal, "NO_DIRECTIONAL_SIGNAL", send=send, account_name=account_name)
        if not self.gate.is_fresh(signal, now=current):
            return self._reject(symbol, signal, "STALE_SIGNAL", send=send, account_name=account_name)

        key = self.gate.signal_key(signal, symbol=symbol)
        with self._lock:
            count = self.database.signal_count(key)
            if count >= 2:
                return self._reject(symbol, signal, "DUPLICATE_SIGNAL_LIMIT", send=send, account_name=account_name)
            if count == 1:
                return self._reject(symbol, signal, "REMINDER_PENDING", send=send, account_name=account_name)
            if not can_open_trade(account):
                return self._reject(symbol, signal, "ACCOUNT_DAILY_LIMIT", send=send, account_name=account_name)
            if candles_1h.empty:
                return self._reject(symbol, signal, "MISSING_SIGNAL_CANDLE", send=send, account_name=account_name)

            candle = candles_1h.iloc[-1]
            entry = float(current_price)
            if signal.signal == "BUY":
                sl = float(candle.low)
                distance = entry - sl
                tp = entry + 2 * distance
            else:
                sl = float(candle.high)
                distance = sl - entry
                tp = entry - 2 * distance
            if distance <= 0:
                return self._reject(symbol, signal, "INVALID_SWEEP_RISK", send=send, account_name=account_name)

            qty = RISK_PER_TRADE_INR / distance
            plan = TradePlan("Sweep V2", signal.signal, signal.timestamp, entry, sl, tp)
            trade = PaperTrade(plan=plan, account=account_name, quantity=qty)
            age_m = int(self.gate.age_hours(signal, now=current) * 60)
            age = f"{age_m} min ago" if age_m < 60 else f"{age_m // 60} hr {age_m % 60} min ago"
            # LOCKED RULE: all Telegram signal messages use the canonical 1H timeframe.
            message = render_signal_message(
                signal,
                symbol=f"{symbol}.NS",
                asset=symbol,
                market="NSE",
                timeframe="1H",
                entry=entry,
                stop_loss=sl,
                take_profit=tp,
                quantity=qty,
                risk=trade.planned_risk,
                account=account_name,
                freshness="FRESH",
                age_str=age,
            )
            if not send:
                return SweepDispatchResult(symbol, signal, trade, message, False, "READY_TO_SEND", account_name)

            send_message(message, self.telegram_config or TelegramConfig.from_env())
            self.gate.accept(signal, symbol=symbol, now=current)
            self.database.record_signal_send(
                key,
                current.isoformat(),
                (current + pd.Timedelta(hours=1)).isoformat(),
                message.text,
                {
                    "strategy": "Sweep V2",
                    "symbol": symbol,
                    "direction": signal.signal,
                    "timestamp": signal.timestamp.isoformat(),
                },
            )
            updated = register_trade(account, planned_risk=trade.planned_risk)
            self.accounts[account_name] = updated
            self.database.save_account(
                account_name,
                balance=updated.balance,
                trades_today=updated.trades_today,
                planned_risk_used=updated.planned_risk_used,
                reset_date=current.date().isoformat(),
            )
            return SweepDispatchResult(symbol, signal, trade, message, True, "SENT_AND_ACCEPTED", account_name)

    def scan_universe_and_dispatch(self, *, now=None, period="30d", send=True):
        out = []
        for symbol in NSE_15_SYMBOLS:
            try:
                signal, frame = self.scan_symbol(symbol, period=period)
                if signal.signal not in ("BUY", "SELL"):
                    out.append(self.dispatch(symbol, signal, frame, current_price=0.0, now=now, send=send))
                    continue
                data = self.runtime.provider.fetch(
                    f"{symbol}.NS", period="1d", interval="1m", validate_hourly=False
                )
                if data.empty:
                    continue
                out.append(
                    self.dispatch(
                        symbol,
                        signal,
                        frame,
                        current_price=float(data.close.iloc[-1]),
                        now=now,
                        send=send,
                    )
                )
            except Exception:
                continue
        return out


__all__ = ["SweepDispatchResult", "SweepService"]
