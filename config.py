"""Central configuration for MULTIBOT2."""

from __future__ import annotations

import os
from dataclasses import dataclass

IST_TIMEZONE = "Asia/Kolkata"

# These are deliberately configuration boundaries, not strategy assumptions.
DEFAULT_TIMEFRAME = "1h"
DEFAULT_FRESHNESS_HOURS = 1


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    timezone: str = IST_TIMEZONE
    timeframe: str = DEFAULT_TIMEFRAME
    freshness_hours: int = DEFAULT_FRESHNESS_HOURS

    market_data_provider: str | None = None

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    dashboard_api_url: str = "/api/dashboard"

    @classmethod
    def from_env(cls) -> "Settings":
        freshness = os.getenv(
            "FRESHNESS_HOURS",
            str(DEFAULT_FRESHNESS_HOURS),
        )

        try:
            freshness_hours = int(freshness)
        except ValueError as exc:
            raise ValueError("FRESHNESS_HOURS must be an integer") from exc

        if freshness_hours <= 0:
            raise ValueError("FRESHNESS_HOURS must be greater than zero")

        return cls(
            timezone=os.getenv("TIMEZONE", IST_TIMEZONE),
            timeframe=os.getenv("TIMEFRAME", DEFAULT_TIMEFRAME),
            freshness_hours=freshness_hours,
            market_data_provider=os.getenv("MARKET_DATA_PROVIDER"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            dashboard_api_url=os.getenv(
                "DASHBOARD_API_URL",
                "/api/dashboard",
            ),
        )


settings = Settings.from_env()
