from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    app_env: str = "development"
    app_name: str = "mavis"
    log_level: str = "INFO"
    market_data_provider: str | None = None
    default_market_timezone: str = "Asia/Kolkata"
    scheduler_enabled: bool = False
    paper_trading_enabled: bool = True
    live_broker_enabled: bool = False
    data_request_timeout_seconds: int = 20
    max_retries: int = 3
    retry_backoff_seconds: int = 2

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_env=os.getenv("APP_ENV", "development"),
            app_name=os.getenv("APP_NAME", "mavis"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            market_data_provider=os.getenv("MARKET_DATA_PROVIDER"),
            default_market_timezone=os.getenv("DEFAULT_MARKET_TIMEZONE", "Asia/Kolkata"),
            scheduler_enabled=_bool_env("SCHEDULER_ENABLED", False),
            paper_trading_enabled=_bool_env("PAPER_TRADING_ENABLED", True),
            live_broker_enabled=_bool_env("LIVE_BROKER_ENABLED", False),
            data_request_timeout_seconds=int(os.getenv("DATA_REQUEST_TIMEOUT_SECONDS", "20")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_backoff_seconds=int(os.getenv("RETRY_BACKOFF_SECONDS", "2")),
        )

    def validate_safety(self) -> None:
        if self.live_broker_enabled:
            raise ValueError("LIVE_BROKER_ENABLED must remain false for the initial paper-trading baseline")
        if self.data_request_timeout_seconds <= 0:
            raise ValueError("DATA_REQUEST_TIMEOUT_SECONDS must be positive")
        if self.max_retries < 0:
            raise ValueError("MAX_RETRIES cannot be negative")


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")
