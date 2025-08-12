"""Logging setup and configuration using Loguru.

This module configures structured JSON logging for the entire application.
"""

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO

from loguru import logger as loguru_logger

if TYPE_CHECKING:
    from loguru import Logger

from app.core.config.config import settings
from app.core.config.logging_sink import LoggingSink


def _build_sink_kwargs(
    sink: LoggingSink,
    sink_target: str | TextIO,
    json_format: str,
    pretty_format: str,
) -> dict[str, Any]:
    """Build keyword arguments for configuring a Loguru sink.

    Args:     sink (LoggingSinkConfig): The sink configuration object.     sink_target
    (str | TextIO): The sink target (e.g., file path or sys.stdout).     json_format
    (str): The log format string for JSON/file sinks.     pretty_format (str): The log
    format string for pretty/color console sinks.

    Returns:     dict[str, Any]: Keyword arguments for loguru_logger.add().
    """
    if sink_target == sys.stdout:
        log_format = pretty_format

        def filter_request_id(record: dict[str, Any]) -> bool:
            req_id = record["extra"].get("request_id")
            if req_id in ("NULL", "-"):
                record["extra"]["colored_request_id"] = ""
                record["extra"]["colored_separator"] = ""
            elif req_id:
                record["extra"]["colored_request_id"] = req_id
                record["extra"]["colored_separator"] = " | "
            else:
                record["extra"]["colored_request_id"] = ""
                record["extra"]["colored_separator"] = ""
            return True

        kwargs = {
            "level": sink.level or "INFO",
            "format": log_format,
            "serialize": bool(sink.serialize),
            "backtrace": bool(sink.backtrace),
            "diagnose": bool(sink.diagnose),
            "enqueue": bool(sink.enqueue),
            "filter": filter_request_id,
            "colorize": True,
            "catch": bool(sink.catch),
        }
    else:
        log_format = json_format
        kwargs = {
            "level": sink.level or "INFO",
            "format": log_format,
            "serialize": bool(sink.serialize),
            "backtrace": bool(sink.backtrace),
            "diagnose": bool(sink.diagnose),
            "enqueue": bool(sink.enqueue),
            "filter": sink.filter,
            "colorize": bool(sink.colorize),
            "catch": bool(sink.catch),
        }
    return kwargs


def configure_logging() -> None:
    """Configure global application logging using Loguru and settings-based config."""
    # Disable noisy HTTP logging from httpx and HTTP core
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpcore.connection").setLevel(logging.WARNING)
    logging.getLogger("httpcore.http11").setLevel(logging.WARNING)

    loguru_logger.remove()

    # Always set extra["request_id"] if missing
    def patch_record(record: dict[str, Any]) -> None:
        record["extra"].setdefault("request_id", "NULL")

    loguru_logger.configure(patcher=patch_record)

    json_format = (
        '{{"timestamp":"{time:YYYY-MM-DDTHH:mm:ss.SSSZ}",'
        '"level":"{level}","logger":"{name}","request_id":"{extra[request_id]}","msg":{message!r}}}'
    )
    pretty_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>"
        "{extra[colored_separator]}<blue>{extra[colored_request_id]}</blue>"
        " | <level>{message}</level>"
    )

    for sink in settings.logging_sinks:
        sink_target = sys.stdout if sink.sink == "sys.stdout" else sink.sink

        kwargs = _build_sink_kwargs(sink, sink_target, json_format, pretty_format)

        if isinstance(sink_target, str) and sink_target != "sys.stdout":
            log_path = Path(sink_target).expanduser().resolve()
            log_dir = log_path.parent
            log_dir.mkdir(parents=True, exist_ok=True)
            if getattr(sink, "rotation", None):
                kwargs["rotation"] = sink.rotation
            if getattr(sink, "retention", None):
                kwargs["retention"] = sink.retention
            if getattr(sink, "compression", None):
                kwargs["compression"] = sink.compression

        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        loguru_logger.add(sink_target, **kwargs)


def get_logger(name: str | None = None) -> "Logger":
    """Retrieve a configured Loguru logger instance.

    Args:
        name (str | None): Optional logical name to bind to the logger.

    Returns:
        A Loguru logger, optionally bound with a custom name.
    """
    return loguru_logger.bind(name=name) if name else loguru_logger
