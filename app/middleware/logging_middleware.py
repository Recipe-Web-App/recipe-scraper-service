"""Logging middleware.

Implements middleware to log incoming requests and responses, helping with debugging and
monitoring. Also intercepts Uvicorn logs to ensure they are handled by the application's
logging system.
"""

import logging

from app.core.logging import get_logger

uvicorn_logger = get_logger("uvicorn")


class InterceptHandler(logging.Handler):
    """Intercept standard logging and route to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to Loguru.

        Args:     record (logging.LogRecord): The log record to emit.
        """
        try:
            level = uvicorn_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        uvicorn_logger.opt(depth=6).log(level, record.getMessage())
