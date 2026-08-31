"""Application configuration for MULTIBOT2.

Only configuration structure belongs here. Strategy, provider, Telegram,
and risk decisions that are not yet frozen are deliberately not invented.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings read from environment variables."""

    environment: str = "development"
    timezone: str = "Asia/Kolkata"

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            environment=os.getenv("MULTIBOT2_ENV", "development"),
            timezone=os.getenv("MULTIBOT2_TIMEZONE", "Asia/Kolkata"),
        )


def get_settings() -> Settings:
    """Return the current immutable application settings."""
    return Settings.from_environment()
