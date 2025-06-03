"""Logging setup and configuration using Loguru.

This module configures structured JSON logging for the entire application.
"""

import sys
from pathlib import Path

from loguru import _Logger
from loguru import logger as loguru_logger

from app.core.config import settings


def configure_logging() -> None:
    """Configure global application logging using Loguru and settings-based config.

    Ensures log directories exist for file sinks before configuring Loguru.
    """
    loguru_logger.remove()
    for sink in settings.logging_sinks:
        sink_target = sys.stdout if sink.sink == "sys.stdout" else sink.sink

        # Ensure log directory exists for file sinks
        if isinstance(sink_target, str) and sink_target != "sys.stdout":
            log_path = Path(sink_target).expanduser().resolve()
            log_dir = log_path.parent
            log_dir.mkdir(parents=True, exist_ok=True)

        loguru_logger.add(
            sink_target,
            level=sink.level or "INFO",
            format=sink.format,
            serialize=sink.serialize if sink.serialize is not None else False,
            rotation=sink.rotation,
            retention=sink.retention,
            compression=sink.compression,
            backtrace=sink.backtrace,
            diagnose=sink.diagnose,
            enqueue=sink.enqueue,
            filter=sink.filter,
            colorize=sink.colorize,
            catch=sink.catch,
        )


def get_logger(name: str | None = None) -> _Logger:
    """Retrieve a configured Loguru logger instance.

    Args:
        name (str | None): Optional logical name to bind to the logger.

    Returns:
        _Logger: A Loguru logger, optionally bound with a custom name.
    """
    return loguru_logger.bind(name=name) if name else loguru_logger
