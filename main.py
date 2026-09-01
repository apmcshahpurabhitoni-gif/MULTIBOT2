"""MULTIBOT2 application entry point and TrendPulse runtime boundary."""

from __future__ import annotations

import logging

import pandas as pd

from config import (
    DEFAULT_TIMEFRAME,
    IST_TIMEZONE,
    SIGNAL_FRESHNESS_HOURS,
    settings,
    validate_configuration,
)
from trendpulse_service import TrendPulseDispatchResult, TrendPulseService
from yahoo_provider import YahooProvider


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("multibot2")

_TRENDPULSE_SERVICE: TrendPulseService | None = None


def validate_runtime_configuration() -> None:
    """Validate canonical runtime configuration."""

    validate_configuration()

    if settings.timezone != IST_TIMEZONE:
        raise ValueError(
            "MULTIBOT2 requires Asia/Kolkata as the canonical timezone"
        )

    if settings.timeframe != DEFAULT_TIMEFRAME:
        raise ValueError(
            "MULTIBOT2 currently requires the 1h canonical timeframe"
        )

    if settings.freshness_hours != SIGNAL_FRESHNESS_HOURS:
        raise ValueError(
            "MULTIBOT2 requires a 1-hour signal freshness boundary"
        )

    if settings.market_data_provider != "yahoo":
        raise ValueError(
            "MULTIBOT2 requires Yahoo Finance as the market-data provider"
        )


def build_market_data_provider() -> YahooProvider:
    """Build the canonical market-data provider."""

    if settings.market_data_provider != "yahoo":
        raise ValueError(
            "Only Yahoo Finance is supported as the canonical provider"
        )

    return YahooProvider()


def build_trendpulse_service() -> TrendPulseService:
    """Return the process-wide TrendPulse service.

    Keeping one service instance alive preserves the SignalGate duplicate
    history between scanner cycles within the running process.
    """
    global _TRENDPULSE_SERVICE

    validate_runtime_configuration()

    if _TRENDPULSE_SERVICE is None:
        _TRENDPULSE_SERVICE = TrendPulseService()

    return _TRENDPULSE_SERVICE


def run_trendpulse_cycle(
    *,
    now: pd.Timestamp | None = None,
    period: str = "5d",
    send: bool = True,
) -> list[TrendPulseDispatchResult]:
    """Run one complete TrendPulse scan/dispatch cycle.

    ``send=True`` is the production path. Tests and diagnostics can use
    ``send=False`` to render and validate messages without contacting Telegram.
    """
    service = build_trendpulse_service()
    results = service.scan_universe_and_dispatch(
        now=now,
        period=period,
        send=send,
    )

    sent = sum(result.sent for result in results)
    logger.info(
        "TrendPulse cycle complete: %d symbols, %d Telegram messages sent",
        len(results),
        sent,
    )
    return results


def main() -> None:
    """Validate and initialize MULTIBOT2 without automatically sending signals."""

    validate_runtime_configuration()

    market_data_provider = build_market_data_provider()

    logger.info("MULTIBOT2 starting")
    logger.info(
        "Timezone: %s",
        settings.timezone,
    )
    logger.info(
        "Timeframe: %s",
        settings.timeframe,
    )
    logger.info(
        "Signal freshness: %s hour",
        settings.freshness_hours,
    )
    logger.info("Market-data provider: Yahoo Finance")
    logger.info(
        "Yahoo provider initialized: %s",
        type(market_data_provider).__name__,
    )
    logger.info(
        "Telegram: %s",
        "CONFIGURED"
        if settings.telegram_bot_token
        and settings.telegram_chat_id
        else "NOT_CONFIGURED",
    )
    logger.info("MULTIBOT2 runtime initialized")


if __name__ == "__main__":
    main()
