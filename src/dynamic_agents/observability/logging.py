"""Secret-safe structured logging setup."""

import logging
from typing import Any

import structlog

from dynamic_agents.security.redaction import redact


def configure_logging(level: str = "INFO", json_logs: bool = False) -> None:
    """Configure stdlib and structlog output."""
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format="%(message)s")
    processors: list[Any] = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
    ]
    processors.append(
        structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=processors, wrapper_class=structlog.make_filtering_bound_logger(level.upper())
    )


def safe_message(value: str) -> str:
    return redact(value)
