"""MULTIBOT2 application entry point."""

from __future__ import annotations

import logging

from config import settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("multibot2")


def validate_runtime_configuration() -> None:
    """Validate configuration that is safe to validate at startup."""

    if settings.timezone != "Asia/Kolkata":
        raise ValueError(
            "MULTIBOT2 requires Asia/Kolkata as the canonical timezone"
        )

    if settings.timeframe != "1h":
        raise ValueError(
            "MULTIBOT2 currently requires the 1h canonical timeframe"
        )

    if settings.freshness_hours != 1:
        raise ValueError(
            "MULTIBOT2 requires a 1-hour signal freshness boundary"
        )


def main() -> None:
    """Start the MULTIBOT2 application."""

    validate_runtime_configuration()

    logger.info("MULTIBOT2 starting")
    logger.info("Timezone: %s", settings.timezone)
    logger.info("Timeframe: %s", settings.timeframe)
    logger.info(
        "Signal freshness: %s hour",
        settings.freshness_hours,
    )

    logger.info(
        "Market-data provider: %s",
        settings.market_data_provider or "NOT_CONFIGURED",
    )

    logger.info(
        "Telegram: %s",
        "CONFIGURED"
        if settings.telegram_bot_token
        and settings.telegram_chat_id
        else "NOT_CONFIGURED",
    )

    logger.info(
        "MULTIBOT2 runtime initialized"
    )


if __name__ == "__main__":
    main()
