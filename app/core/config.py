"""Application configuration settings.

Defines and loads configuration variables and settings used across the application,
including environment-specific and default configurations.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import Field, PrivateAttr
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass(frozen=True)
class LoggingSink:
    """Represents a single logging sink configuration.

    Attributes:
        sink (Any): The sink target (e.g., file path or sys.stdout).
        level (str | None): The log level for this sink.
        format (str | None): The log message format.
        serialize (bool | None): Whether to serialize logs as JSON.
        rotation (str | None): Log rotation policy.
        retention (str | None): Log retention policy.
        compression (str | None): Compression for rotated logs.
        backtrace (bool | None): Enable better tracebacks.
        diagnose (bool | None): Enable better exception diagnosis.
        enqueue (bool | None): Use multiprocessing-safe queue.
        filter (Callable | dict | str | None): Filter for log records.
        colorize (bool | None): Enable colored output.
        catch (bool | None): Catch sink exceptions.
    """

    sink: Any
    level: str | None = None
    format: str | None = None
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

        Args:
            data (dict[str, Any]): Dictionary containing sink configuration.

        Returns:
            LoggingSink: The constructed LoggingSink instance.
        """
        return LoggingSink(
            sink=data.get("sink"),
            level=data.get("level"),
            format=data.get("format"),
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


class _Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    POSTGRES_HOST: str = Field(..., alias="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(..., alias="POSTGRES_PORT")
    POSTGRES_DB: str = Field(..., alias="POSTGRES_DB")
    POSTGRES_SCHEMA: str = Field(..., alias="POSTGRES_SCHEMA")
    RECIPE_SCRAPER_DB_USER: str = Field(..., alias="RECIPE_SCRAPER_DB_USER")
    RECIPE_SCRAPER_DB_PASSWORD: str = Field(..., alias="RECIPE_SCRAPER_DB_PASSWORD")

    LOGGING_CONFIG_PATH: str = Field(
        "../config/logging.json",
        alias="LOGGING_CONFIG_PATH",
    )

    _LOGGING_SINKS: list[LoggingSink] = PrivateAttr(default_factory=list)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        validate_default=True,
    )

    def __post_init_post_parse__(self) -> None:
        """Load logging config after Pydantic initialization."""
        config_path = Path(self.LOGGING_CONFIG_PATH).resolve()
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
        sinks = config.get("sinks", [])
        self._LOGGING_SINKS = [
            LoggingSink.from_dict(s) for s in sinks if isinstance(s, dict)
        ]

    @property
    def postgres_host(self) -> str:
        return self.POSTGRES_HOST

    @property
    def postgres_port(self) -> int:
        return self.POSTGRES_PORT

    @property
    def postgres_db(self) -> str:
        return self.POSTGRES_DB

    @property
    def postgres_schema(self) -> str:
        return self.POSTGRES_SCHEMA

    @property
    def recipe_scraper_db_user(self) -> str:
        return self.RECIPE_SCRAPER_DB_USER

    @property
    def recipe_scraper_db_password(self) -> str:
        return self.RECIPE_SCRAPER_DB_PASSWORD

    @property
    def logging_sinks(self) -> list[LoggingSink]:
        return self._LOGGING_SINKS

    @property
    def logging_stdout_sink(self) -> LoggingSink | None:
        return next(
            (sink for sink in self._LOGGING_SINKS if sink.sink == "sys.stdout"),
            None,
        )

    @property
    def logging_file_sink(self) -> LoggingSink | None:
        return next(
            (
                sink
                for sink in self._LOGGING_SINKS
                if isinstance(sink.sink, str) and sink.sink.endswith(".log")
            ),
            None,
        )


settings = _Settings()
