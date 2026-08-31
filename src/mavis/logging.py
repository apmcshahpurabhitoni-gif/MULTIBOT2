from __future__ import annotations

import logging


_RESERVED = {"message", "asctime", "levelname", "name"}


def configure_logging(level: str = "INFO") -> None:
    """Configure one application-wide structured-friendly logger."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )


def get_logger(name: str = "mavis") -> logging.Logger:
    return logging.getLogger(name)


def event(logger: logging.Logger, name: str, **fields: object) -> None:
    """Emit a stable key/value event without mutating caller data."""
    safe = {key: value for key, value in fields.items() if key not in _RESERVED}
    rendered = " ".join(f"{key}={safe[key]!r}" for key in sorted(safe))
    logger.info("event=%s%s", name, f" {rendered}" if rendered else "")
