"""Logging setup and configuration using Loguru.

This module configures structured JSON logging for the entire application.
"""

import json
import sys

from loguru import _Logger
from loguru import logger as loguru_logger


def configure_logging() -> None:
    """Configure global application logging using Loguru with JSON formatting."""
    loguru_logger.remove()
    loguru_logger.add(
        sys.stdout,
        format=lambda record: json.dumps(
            {
                "timestamp": record["time"].isoformat(),
                "level": record["level"].name,
                "logger": record["name"],
                "msg": record["message"],
                "function": record["function"],
                "line": record["line"],
                "module": record["module"],
            },
        ),
        serialize=False,
        level="INFO",
    )


def get_logger(name: str | None = None) -> _Logger:
    """Retrieve a configured Loguru logger instance.

    Args:
        name (str | None): Optional logical name to bind to the logger.

    Returns:
        _Logger: A Loguru logger, optionally bound with a custom name.
    """
    return loguru_logger.bind(name=name) if name else loguru_logger
