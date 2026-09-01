"""Central configuration for MULTIBOT2.

All frozen project-level rules belong here.
Secrets are never hard-coded.
Runtime credentials are loaded from environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


# ============================================================
# CORE MARKET RULES
# ============================================================

IST_TIMEZONE = "Asia/Kolkata"
DEFAULT_TIMEFRAME = "1h"
SIGNAL_FRESHNESS_HOURS = 1
NSE_MARKET_OPEN = "09:15"
NSE_MARKET_CLOSE = "15:30"


# ============================================================
# MARKET-DATA PROVIDER
# ============================================================

MARKET_DATA_PROVIDER = "yahoo"


# ============================================================
# HARD-CODED NSE-15 UNIVERSE
# ============================================================

NSE_15_SYMBOLS: tuple[str, ...] = (
    "RELIANCE",
    "BHARTIARTL",
    "HDFCBANK",
    "ICICIBANK",
    "SBIN",
    "TCS",
    "BAJFINANCE",
    "LT",
    "LICI",
    "SUNPHARMA",
    "HINDUNILVR",
    "INFY",
    "TITAN",
    "MARUTI",
    "KOTAKBANK",
)


# ============================================================
# PAPER-TRADING RULES
# ============================================================

ACCOUNT_SIZE_INR = 100_000
RISK_PER_TRADE_INR = 2_000

# Original MULTIBOT account-specific daily limits.
# These are independent: reaching one account's limit does not
# consume capacity in the other logical accounts.
ACCOUNT_TRADE_LIMITS: dict[str, int] = {
    "macro": 20,
    "nifty": 5,
    "ny_session": 3,
    "sweep_4h": 3,
}

# Legacy compatibility value retained for modules/tests that use the
# former single-limit configuration. Actual runtime enforcement uses
# ACCOUNT_TRADE_LIMITS per logical account.
MAX_TRADES_PER_DAY = 3
MAX_DAILY_PLANNED_RISK_INR = RISK_PER_TRADE_INR * MAX_TRADES_PER_DAY

LEVERAGE = 1.0


# ============================================================
# FOUR LOGICAL ACCOUNTS
# ============================================================

ACCOUNT_NAMES: tuple[str, ...] = (
    "macro",
    "nifty",
    "ny_session",
    "sweep_4h",
)


# ============================================================
# ENVIRONMENT CONFIGURATION
# ============================================================

@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    timezone: str = IST_TIMEZONE
    timeframe: str = DEFAULT_TIMEFRAME
    freshness_hours: int = SIGNAL_FRESHNESS_HOURS

    market_data_provider: str = MARKET_DATA_PROVIDER

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    dashboard_api_url: str = "/api/dashboard"

    @classmethod
    def from_env(cls) -> "Settings":
        """Load runtime settings from environment variables."""

        freshness = os.getenv(
            "FRESHNESS_HOURS",
            str(SIGNAL_FRESHNESS_HOURS),
        )

        try:
            freshness_hours = int(freshness)
        except ValueError as exc:
            raise ValueError(
                "FRESHNESS_HOURS must be an integer"
            ) from exc

        if freshness_hours <= 0:
            raise ValueError(
                "FRESHNESS_HOURS must be greater than zero"
            )

        timezone = os.getenv(
            "TIMEZONE",
            IST_TIMEZONE,
        )

        if timezone != IST_TIMEZONE:
            raise ValueError(
                "TIMEZONE must be Asia/Kolkata"
            )

        timeframe = os.getenv(
            "TIMEFRAME",
            DEFAULT_TIMEFRAME,
        )

        if timeframe != DEFAULT_TIMEFRAME:
            raise ValueError(
                "TIMEFRAME must be 1h"
            )

        provider = os.getenv(
            "MARKET_DATA_PROVIDER",
            MARKET_DATA_PROVIDER,
        ).strip().lower()

        if provider != MARKET_DATA_PROVIDER:
            raise ValueError(
                "MARKET_DATA_PROVIDER must be yahoo"
            )

        return cls(
            timezone=timezone,
            timeframe=timeframe,
            freshness_hours=freshness_hours,
            market_data_provider=provider,
            telegram_bot_token=os.getenv(
                "TELEGRAM_BOT_TOKEN"
            ),
            telegram_chat_id=os.getenv(
                "TELEGRAM_CHAT_ID"
            ),
            dashboard_api_url=os.getenv(
                "DASHBOARD_API_URL",
                "/api/dashboard",
            ),
        )


settings = Settings.from_env()


# ============================================================
# VALIDATION
# ============================================================

def validate_configuration() -> None:
    """Validate all frozen configuration rules."""

    if MARKET_DATA_PROVIDER != "yahoo":
        raise ValueError(
            "MULTIBOT2 market-data provider must be Yahoo Finance"
        )

    if settings.market_data_provider != "yahoo":
        raise ValueError(
            "MULTIBOT2 runtime provider must be Yahoo Finance"
        )

    if len(NSE_15_SYMBOLS) != 15:
        raise ValueError(
            "NSE universe must contain exactly 15 symbols"
        )

    if len(set(NSE_15_SYMBOLS)) != 15:
        raise ValueError(
            "NSE universe contains duplicate symbols"
        )

    if ACCOUNT_SIZE_INR <= 0:
        raise ValueError(
            "Account size must be positive"
        )

    if RISK_PER_TRADE_INR <= 0:
        raise ValueError(
            "Risk per trade must be positive"
        )

    if MAX_TRADES_PER_DAY <= 0:
        raise ValueError(
            "Legacy maximum trades per day must be positive"
        )

    if MAX_DAILY_PLANNED_RISK_INR != RISK_PER_TRADE_INR * MAX_TRADES_PER_DAY:
        raise ValueError(
            "Legacy daily risk configuration is inconsistent"
        )

    if set(ACCOUNT_TRADE_LIMITS) != set(ACCOUNT_NAMES):
        raise ValueError(
            "Per-account trade limits must cover all logical accounts"
        )

    if any(limit <= 0 for limit in ACCOUNT_TRADE_LIMITS.values()):
        raise ValueError(
            "Per-account trade limits must be positive"
        )

    if LEVERAGE != 1.0:
        raise ValueError(
            "MULTIBOT2 uses 1x / no leverage"
        )


validate_configuration()
