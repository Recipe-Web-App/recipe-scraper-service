"""Logging configuration using Loguru.

This module provides:
- Structured JSON logging for production
- Human-readable colorized output for development
- Request ID correlation via context
- Intercept standard library logging
- File rotation and retention policies
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from typing import Any


# Context variable for request-scoped data (request_id, user_id, etc.)
_log_context: ContextVar[dict[str, Any]] = ContextVar("log_context", default={})


class InterceptHandler(logging.Handler):
    """Intercept standard library logging and redirect to Loguru.

    This allows third-party libraries using standard logging
    to have their logs processed by Loguru.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record by forwarding to Loguru."""
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where the logged message originated
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def _format_record(record: dict[str, Any]) -> str:
    """Format log record with context variables for JSON serialization."""
    # Get context from ContextVar
    context = _log_context.get()

    # Add context to the record's extra dict
    record["extra"].update(context)

    # Format for JSON output
    serialize_fields = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "logger": record["name"],
        "function": record["function"],
        "line": record["line"],
        **record["extra"],
    }

    # Add exception info if present
    if record["exception"]:
        serialize_fields["exception"] = {
            "type": record["exception"].type.__name__ if record["exception"].type else None,
            "value": str(record["exception"].value) if record["exception"].value else None,
            "traceback": record["exception"].traceback,
        }

    # Return JSON-serialized record
    import orjson
    return orjson.dumps(serialize_fields).decode() + "\n"


def _format_record_dev(record: dict[str, Any]) -> str:
    """Format log record for development (human-readable with context)."""
    context = _log_context.get()

    # Build context string
    context_str = ""
    if context:
        context_parts = [f"{k}={v}" for k, v in context.items()]
        context_str = f" | {' '.join(context_parts)}"

    # Standard format with optional context
    fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>"
        f"{context_str} - "
        "<level>{message}</level>\n"
    )

    if record["exception"]:
        fmt += "{exception}\n"

    return fmt


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    *,
    is_development: bool = False,
    log_file: Path | str | None = None,
) -> None:
    """Configure Loguru logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ("json" or "text")
        is_development: Enable development-friendly formatting
        log_file: Optional file path for log output with rotation
    """
    # Remove default handler
    logger.remove()

    # Determine format based on environment
    use_json = log_format == "json" and not is_development

    if use_json:
        # JSON format for production
        logger.add(
            sys.stdout,
            format=_format_record,
            level=log_level.upper(),
            colorize=False,
            serialize=False,  # We handle serialization in _format_record
            backtrace=True,
            diagnose=False,  # Disable in production for security
        )
    else:
        # Human-readable format for development
        logger.add(
            sys.stdout,
            format=_format_record_dev,
            level=log_level.upper(),
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

    # Optional file logging with rotation
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_path,
            format=_format_record,
            level=log_level.upper(),
            rotation="100 MB",
            retention="7 days",
            compression="gz",
            serialize=False,
            backtrace=True,
            diagnose=False,
        )

    # Intercept standard library logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Reduce noise from third-party libraries
    for logger_name in [
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "sqlalchemy.engine",
        "httpx",
        "httpcore",
        "asyncio",
        "arq",
    ]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str) -> "logger":  # type: ignore[valid-type]
    """Get a logger instance bound to a name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        A Loguru logger instance
    """
    return logger.bind(name=name)


def bind_context(**kwargs: Any) -> None:
    """Bind context variables for structured logging.

    Context variables are automatically included in all subsequent
    log entries within the same async context (e.g., request lifecycle).

    Args:
        **kwargs: Key-value pairs to bind to the logging context

    Example:
        bind_context(request_id="abc-123", user_id="user-456")
    """
    current = _log_context.get().copy()
    current.update(kwargs)
    _log_context.set(current)


def clear_context() -> None:
    """Clear all context variables.

    Should be called at the start of each request to ensure
    clean logging context.
    """
    _log_context.set({})


def unbind_context(*keys: str) -> None:
    """Remove specific context variables.

    Args:
        *keys: Keys to remove from the logging context
    """
    current = _log_context.get().copy()
    for key in keys:
        current.pop(key, None)
    _log_context.set(current)


def get_context() -> dict[str, Any]:
    """Get the current logging context.

    Returns:
        Dictionary of current context variables
    """
    return _log_context.get().copy()


# Re-export the main logger for convenience
__all__ = [
    "logger",
    "get_logger",
    "setup_logging",
    "bind_context",
    "clear_context",
    "unbind_context",
    "get_context",
]
