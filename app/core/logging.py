"""Logging setup and configuration using Loguru.

This module configures structured JSON logging for the entire application.
"""

import sys
from pathlib import Path

from loguru import _Logger
from loguru import logger as loguru_logger

from app.core.config.config import settings


def configure_logging() -> None:
    """Configure global application logging using Loguru and settings-based config."""
    loguru_logger.remove()

    # JSON format for files, pretty/color for console
    json_format = (
        '{{"timestamp":"{time:YYYY-MM-DDTHH:mm:ss.SSSZ}",'
        '"level":"{level}","logger":"{name}","msg":{message!r}}}'
    )
    pretty_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    for sink in settings.logging_sinks:
        sink_target = sys.stdout if sink.sink == "sys.stdout" else sink.sink

        log_format = pretty_format if sink_target == sys.stdout else json_format

        kwargs = {
            "level": sink.level or "INFO",
            "format": log_format,
            "serialize": sink.serialize if sink.serialize is not None else False,
            "backtrace": sink.backtrace,
            "diagnose": sink.diagnose,
            "enqueue": sink.enqueue,
            "filter": sink.filter,
            "colorize": sink.colorize,
            "catch": sink.catch,
        }

        if isinstance(sink_target, str) and sink_target != "sys.stdout":
            log_path = Path(sink_target).expanduser().resolve()
            log_dir = log_path.parent
            log_dir.mkdir(parents=True, exist_ok=True)
            if sink.rotation:
                kwargs["rotation"] = sink.rotation
            if sink.retention:
                kwargs["retention"] = sink.retention
            if sink.compression:
                kwargs["compression"] = sink.compression

        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        loguru_logger.add(sink_target, **kwargs)


def get_logger(name: str | None = None) -> _Logger:
    """Retrieve a configured Loguru logger instance.

    Args:
        name (str | None): Optional logical name to bind to the logger.

    Returns:
        _Logger: A Loguru logger, optionally bound with a custom name.
    """
    return loguru_logger.bind(name=name) if name else loguru_logger
