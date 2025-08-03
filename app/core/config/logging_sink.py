"""Represents a logging sink configuration.

This class encapsulates the configuration for a single logging sink used in the
application.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LoggingSink:
    """Represents a single logging sink configuration.

    Attributes:     sink (Any): The sink target (e.g., file path or sys.stdout). level
    (str | None): The log level for this sink.     serialize (bool | None): Whether to
    serialize logs as JSON.     rotation (str | None): Log rotation policy. retention
    (str | None): Log retention policy.     compression (str | None): Compression for
    rotated logs.     backtrace (bool | None): Enable better tracebacks. diagnose (bool
    | None): Enable better exception diagnosis.     enqueue (bool | None): Use
    multiprocessing-safe queue.     filter (Callable | dict | str | None): Filter for
    log records.     colorize (bool | None): Enable colored output.     catch (bool |
    None): Catch sink exceptions.
    """

    sink: Any
    level: str | None = None
    serialize: bool | None = None
    rotation: str | None = None
    retention: str | None = None
    compression: str | None = None
    backtrace: bool | None = None
    diagnose: bool | None = None
    enqueue: bool | None = None
    filter: Callable[..., bool] | dict[str, Any] | str | None = None
    colorize: bool | None = None
    catch: bool | None = None

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "LoggingSink":
        """Create a LoggingSink instance from a dictionary.

        Args:     data (dict[str, Any]): Dictionary containing sink configuration.

        Returns:     LoggingSink: The constructed LoggingSink instance.
        """
        return LoggingSink(
            sink=data.get("sink"),
            level=data.get("level"),
            serialize=data.get("serialize"),
            rotation=data.get("rotation"),
            retention=data.get("retention"),
            compression=data.get("compression"),
            backtrace=data.get("backtrace"),
            diagnose=data.get("diagnose"),
            enqueue=data.get("enqueue"),
            filter=data.get("filter"),
            colorize=data.get("colorize"),
            catch=data.get("catch"),
        )
