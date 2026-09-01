"""Signal freshness and duplicate-suppression gate for MULTIBOT2."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock

import pandas as pd

from config import SIGNAL_FRESHNESS_HOURS, IST_TIMEZONE
from strategies import StrategySignal


MAX_MESSAGE_SEND_COUNT = 2


@dataclass
class SignalGate:
    """Reject stale signals and suppress repeated identical signals."""

    max_age_hours: float = SIGNAL_FRESHNESS_HOURS
    max_repeats: int = MAX_MESSAGE_SEND_COUNT
    _counts: dict[str, int] = field(default_factory=dict)
    _lock: RLock = field(
        default_factory=RLock,
        repr=False,
    )

    def __post_init__(self) -> None:
        if self.max_age_hours <= 0:
            raise ValueError(
                "Signal freshness must be greater than zero"
            )

        if self.max_repeats <= 0:
            raise ValueError(
                "Maximum signal repeats must be greater than zero"
            )

    @staticmethod
    def _now() -> pd.Timestamp:
        return pd.Timestamp.now(
            tz=IST_TIMEZONE
        )

    @staticmethod
    def _normalize_timestamp(
        timestamp: pd.Timestamp,
    ) -> pd.Timestamp:
        timestamp = pd.Timestamp(timestamp)

        if timestamp.tzinfo is None:
            raise ValueError(
                "Signal timestamp must be timezone-aware"
            )

        return timestamp.tz_convert(
            IST_TIMEZONE
        )

    def age_hours(
        self,
        signal: StrategySignal,
        *,
        now: pd.Timestamp | None = None,
    ) -> float:
        """Return signal age in hours."""

        timestamp = self._normalize_timestamp(
            signal.timestamp
        )

        current = (
            self._now()
            if now is None
            else self._normalize_timestamp(now)
        )

        age = (
            current - timestamp
        ).total_seconds() / 3600.0

        if age < 0:
            raise ValueError(
                "Signal timestamp cannot be in the future"
            )

        return age

    def is_fresh(
        self,
        signal: StrategySignal,
        *,
        now: pd.Timestamp | None = None,
    ) -> bool:
        """Return True only when signal age is <= one hour."""

        return (
            self.age_hours(
                signal,
                now=now,
            )
            <= self.max_age_hours
        )

    @staticmethod
    def signal_key(
        signal: StrategySignal,
        *,
        symbol: str,
    ) -> str:
        """Create a stable identity for one signal candle."""

        normalized_symbol = (
            symbol.strip().upper()
        )

        if not normalized_symbol:
            raise ValueError(
                "Signal symbol cannot be empty"
            )

        timestamp = (
            SignalGate._normalize_timestamp(
                signal.timestamp
            )
        )

        return "|".join(
            (
                signal.strategy,
                normalized_symbol,
                signal.signal,
                timestamp.isoformat(),
            )
        )

    def repeat_count(
        self,
        signal: StrategySignal,
        *,
        symbol: str,
    ) -> int:
        """Return number of accepted sends for this signal."""

        key = self.signal_key(
            signal,
            symbol=symbol,
        )

        with self._lock:
            return self._counts.get(
                key,
                0,
            )

    def can_send(
        self,
        signal: StrategySignal,
        *,
        symbol: str,
        now: pd.Timestamp | None = None,
    ) -> bool:
        """Check freshness and repeat limit without changing state."""

        if signal.signal not in (
            "BUY",
            "SELL",
            "NEUTRAL",
        ):
            return False

        if not self.is_fresh(
            signal,
            now=now,
        ):
            return False

        return (
            self.repeat_count(
                signal,
                symbol=symbol,
            )
            < self.max_repeats
        )

    def accept(
        self,
        signal: StrategySignal,
        *,
        symbol: str,
        now: pd.Timestamp | None = None,
    ) -> bool:
        """Atomically validate and record one accepted signal send."""

        if not self.is_fresh(
            signal,
            now=now,
        ):
            return False

        if signal.signal not in (
            "BUY",
            "SELL",
            "NEUTRAL",
        ):
            return False

        key = self.signal_key(
            signal,
            symbol=symbol,
        )

        with self._lock:
            current_count = self._counts.get(
                key,
                0,
            )

            if current_count >= self.max_repeats:
                return False

            self._counts[key] = (
                current_count + 1
            )

            return True

    def clear(self) -> None:
        """Clear all in-memory signal history."""

        with self._lock:
            self._counts.clear()

    def snapshot(self) -> dict[str, int]:
        """Return a copy suitable for persistence."""

        with self._lock:
            return dict(self._counts)

    def restore(
        self,
        counts: dict[str, int],
    ) -> None:
        """Restore previously persisted send counts."""

        if not isinstance(counts, dict):
            raise TypeError(
                "Signal counts must be a dictionary"
            )

        cleaned: dict[str, int] = {}

        for key, value in counts.items():
            if not isinstance(key, str):
                continue

            try:
                count = int(value)
            except (
                TypeError,
                ValueError,
            ):
                continue

            if count < 0:
                continue

            cleaned[key] = min(
                count,
                self.max_repeats,
            )

        with self._lock:
            self._counts = cleaned


def signal_status(
    signal: StrategySignal,
    *,
    now: pd.Timestamp | None = None,
    max_age_hours: float = SIGNAL_FRESHNESS_HOURS,
) -> tuple[str, float]:
    """Return canonical FRESH/STALE status and age."""

    gate = SignalGate(
        max_age_hours=max_age_hours
    )

    age = gate.age_hours(
        signal,
        now=now,
    )

    status = (
        "FRESH"
        if age <= max_age_hours
        else "STALE"
    )

    return status, age
