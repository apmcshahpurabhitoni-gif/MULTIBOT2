"""Central, locked configuration for MULTIBOT2."""
from __future__ import annotations

import os
from dataclasses import dataclass

APP_VERSION = "1.1.0"
IST_TIMEZONE = "Asia/Kolkata"
DEFAULT_TIMEFRAME = "1h"
SIGNAL_FRESHNESS_HOURS = 1
NSE_MARKET_OPEN = "09:15"
NSE_MARKET_CLOSE = "15:30"
MARKET_DATA_PROVIDER = "yahoo"
NSE_15_SYMBOLS = (
    "RELIANCE", "BHARTIARTL", "HDFCBANK", "ICICIBANK", "SBIN", "TCS",
    "BAJFINANCE", "LT", "LICI", "SUNPHARMA", "HINDUNILVR", "INFY",
    "TITAN", "MARUTI", "KOTAKBANK",
)
ACCOUNT_SIZE_INR = 100_000
RISK_PER_TRADE_INR = 2_000
ACCOUNT_TRADE_LIMITS = {"macro": 20, "nifty": 5, "ny_session": 3, "sweep_4h": 3}
ACCOUNT_NAMES = ("macro", "nifty", "ny_session", "sweep_4h")
LEVERAGE = 1.0

# Backtesting is informational and may include additional Yahoo-supported assets.
# These symbols do not alter the locked live NSE-15 universe.
BACKTEST_ASSETS = {
    **{
        symbol: {
            "label": symbol,
            "ticker": f"{symbol}.NS",
            "market": "NSE",
            "asset_type": "equity",
            "group": "NSE-15",
        }
        for symbol in NSE_15_SYMBOLS
    },
    "BTC-USD": {
        "label": "Bitcoin",
        "ticker": "BTC-USD",
        "market": "Crypto",
        "asset_type": "crypto",
        "group": "Digital assets",
    },
    "GC=F": {
        "label": "Gold Futures",
        "ticker": "GC=F",
        "market": "COMEX",
        "asset_type": "commodity",
        "group": "Metals",
    },
}

WHAT_IS_NEW = [
    "Forex Factory economic calendar with date and impact filters.",
    "Historical backtests now support NSE-15, Bitcoin and Gold Futures.",
    "Backtest results include daily signal charts and execution statistics.",
    "Fixed the modern yfinance session error that blocked historical tests.",
    "Polished light/dark and modern/neo-brutalist dashboard spacing and controls.",
    "Signals are grouped by candle date and show scan status separately from dispatched history.",
]


@dataclass(frozen=True)
class Settings:
    timezone: str = IST_TIMEZONE
    timeframe: str = DEFAULT_TIMEFRAME
    freshness_hours: int = SIGNAL_FRESHNESS_HOURS
    market_data_provider: str = MARKET_DATA_PROVIDER
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    dashboard_api_url: str = "/api/dashboard"
    db_path: str = "multibot2_state.db"
    scan_interval_seconds: int = 300
    monitor_interval_seconds: int = 20

    @classmethod
    def from_env(cls) -> "Settings":
        timezone = os.getenv("TIMEZONE", IST_TIMEZONE)
        timeframe = os.getenv("TIMEFRAME", DEFAULT_TIMEFRAME)
        provider = os.getenv("MARKET_DATA_PROVIDER", MARKET_DATA_PROVIDER).strip().lower()
        if timezone != IST_TIMEZONE:
            raise ValueError("TIMEZONE must be Asia/Kolkata")
        if timeframe != DEFAULT_TIMEFRAME:
            raise ValueError("TIMEFRAME must be 1h")
        if provider != MARKET_DATA_PROVIDER:
            raise ValueError("MARKET_DATA_PROVIDER must be yahoo")
        return cls(
            timezone,
            timeframe,
            SIGNAL_FRESHNESS_HOURS,
            provider,
            os.getenv("TELEGRAM_BOT_TOKEN"),
            os.getenv("TELEGRAM_CHAT_ID"),
            os.getenv("DASHBOARD_API_URL", "/api/dashboard"),
            os.getenv("BOT_STATE_DB_PATH", "multibot2_state.db"),
            int(os.getenv("SCAN_INTERVAL_SECONDS", "300")),
            int(os.getenv("MONITOR_INTERVAL_SECONDS", "20")),
        )


settings = Settings.from_env()


def validate_configuration() -> None:
    if MARKET_DATA_PROVIDER != "yahoo" or settings.market_data_provider != "yahoo":
        raise ValueError("MULTIBOT2 market-data provider must be Yahoo Finance")
    if len(NSE_15_SYMBOLS) != 15 or len(set(NSE_15_SYMBOLS)) != 15:
        raise ValueError("NSE universe must contain exactly 15 unique symbols")
    if ACCOUNT_SIZE_INR != 100_000 or RISK_PER_TRADE_INR != 2_000:
        raise ValueError("Locked account/risk values were changed")
    if settings.freshness_hours != 1:
        raise ValueError("Signal freshness must remain locked at 1 hour")
    if set(ACCOUNT_TRADE_LIMITS) != set(ACCOUNT_NAMES) or tuple(ACCOUNT_TRADE_LIMITS.values()) != (20, 5, 3, 3):
        raise ValueError("Original independent account limits are required")
    if LEVERAGE != 1.0:
        raise ValueError("MULTIBOT2 uses 1x / no leverage")
    if settings.scan_interval_seconds < 60 or settings.monitor_interval_seconds < 1:
        raise ValueError("Runtime intervals are invalid")


validate_configuration()
