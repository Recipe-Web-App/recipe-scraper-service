"""Application configuration settings.

Defines and loads configuration variables and settings used across the application,
including environment-specific and default configurations.
"""

import json
from pathlib import Path

from pydantic import Field, PrivateAttr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config.logging_sink import LoggingSink


class _Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    POSTGRES_HOST: str = Field(..., alias="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(..., alias="POSTGRES_PORT")
    POSTGRES_DB: str = Field(..., alias="POSTGRES_DB")
    POSTGRES_SCHEMA: str = Field(..., alias="POSTGRES_SCHEMA")
    RECIPE_SCRAPER_DB_USER: str = Field(..., alias="RECIPE_SCRAPER_DB_USER")
    RECIPE_SCRAPER_DB_PASSWORD: str = Field(..., alias="RECIPE_SCRAPER_DB_PASSWORD")

    LOGGING_CONFIG_PATH: str = Field(
        str(
            (
                Path(__file__).parent.parent.parent.parent / "config" / "logging.json"
            ).resolve(),
        ),
        alias="LOGGING_CONFIG_PATH",
    )

    _LOGGING_SINKS: list[LoggingSink] = PrivateAttr(default_factory=list)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        validate_default=True,
    )

    def __init__(self) -> None:
        """Load logging config after Pydantic initialization."""
        super().__init__()
        config_path = Path(self.LOGGING_CONFIG_PATH).expanduser().resolve()

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
