"""Application configuration settings.

Defines and loads configuration variables and settings used across the application,
including environment-specific and default configurations.
"""

import json
from pathlib import Path

import yaml
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
    POPULAR_RECIPE_URLS: list[str] = Field(default_factory=list)
    WEB_SCRAPER_NAV_PREFIXES: list[str] = Field(default_factory=list)
    WEB_SCRAPER_URL_EXCLUDE_KEYWORDS: list[str] = Field(default_factory=list)
    WEB_SCRAPER_EXCLUDE_NAMES: list[str] = Field(default_factory=list)
    WEB_SCRAPER_FOOD_INDICATORS: list[str] = Field(default_factory=list)
    WEB_SCRAPER_CATEGORY_PATTERNS: list[str] = Field(default_factory=list)
    WEB_SCRAPER_SINGLE_WORD_CATEGORIES: list[str] = Field(default_factory=list)
    WEB_SCRAPER_CATEGORY_INDICATORS: list[str] = Field(default_factory=list)

    LOGGING_CONFIG_PATH: str = Field(
        str(
            (
                Path(__file__).parent.parent.parent.parent / "config" / "logging.json"
            ).resolve(),
        ),
        alias="LOGGING_CONFIG_PATH",
    )

    POPULAR_RECIPES_CONFIG_PATH: str = Field(
        str(
            (
                Path(__file__).parent.parent.parent.parent
                / "config"
                / "recipe_scraping"
                / "recipe_blog_urls.json"
            ).resolve(),
        ),
        alias="POPULAR_RECIPES_CONFIG_PATH",
    )

    WEB_SCRAPER_CONFIG_PATH: str = Field(
        str(
            (
                Path(__file__).parent.parent.parent.parent
                / "config"
                / "recipe_scraping"
                / "web_scraper.yaml"
            ).resolve(),
        ),
        alias="WEB_SCRAPER_CONFIG_PATH",
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

        # Load logging configuration
        config_path = Path(self.LOGGING_CONFIG_PATH).expanduser().resolve()
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
        sinks = config.get("sinks", [])
        self._LOGGING_SINKS = [
            LoggingSink.from_dict(s) for s in sinks if isinstance(s, dict)
        ]

        # Load popular recipes configuration
        popular_recipes_path = (
            Path(self.POPULAR_RECIPES_CONFIG_PATH).expanduser().resolve()
        )
        with popular_recipes_path.open("r", encoding="utf-8") as f:
            popular_recipes = json.load(f)
        self.POPULAR_RECIPE_URLS = (
            popular_recipes if isinstance(popular_recipes, list) else []
        )

        # Load web scraper configuration
        try:
            web_scraper_path = Path(self.WEB_SCRAPER_CONFIG_PATH).expanduser().resolve()
            with web_scraper_path.open("r", encoding="utf-8") as f:
                web_scraper_config = yaml.safe_load(f) or {}
        except (FileNotFoundError, yaml.YAMLError):
            # Log warning and use defaults
            web_scraper_config = {}

        self.WEB_SCRAPER_NAV_PREFIXES = web_scraper_config.get(
            "nav_prefixes",
            [],
        )
        self.WEB_SCRAPER_URL_EXCLUDE_KEYWORDS = web_scraper_config.get(
            "url_exclude_keywords",
            [],
        )
        self.WEB_SCRAPER_EXCLUDE_NAMES = web_scraper_config.get(
            "exclude_names",
            [],
        )
        self.WEB_SCRAPER_FOOD_INDICATORS = web_scraper_config.get(
            "food_indicators",
            [],
        )
        self.WEB_SCRAPER_CATEGORY_PATTERNS = web_scraper_config.get(
            "category_patterns",
            [],
        )
        self.WEB_SCRAPER_SINGLE_WORD_CATEGORIES = web_scraper_config.get(
            "single_word_categories",
            [],
        )
        self.WEB_SCRAPER_CATEGORY_INDICATORS = web_scraper_config.get(
            "category_indicators",
            [],
        )

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

    @property
    def popular_recipe_urls(self) -> list[str]:
        """Get the list of popular recipe website URLs."""
        return self.POPULAR_RECIPE_URLS

    # Web scraper configuration properties
    @property
    def web_scraper_nav_prefixes(self) -> list[str]:
        """Get navigation prefixes to exclude from recipe names."""
        return self.WEB_SCRAPER_NAV_PREFIXES

    @property
    def web_scraper_url_exclude_keywords(self) -> list[str]:
        """Get keywords to exclude from recipe URLs."""
        return self.WEB_SCRAPER_URL_EXCLUDE_KEYWORDS

    @property
    def web_scraper_exclude_names(self) -> list[str]:
        """Get recipe names to exclude."""
        return self.WEB_SCRAPER_EXCLUDE_NAMES

    @property
    def web_scraper_food_indicators(self) -> list[str]:
        """Get food indicators for recipe name validation."""
        return self.WEB_SCRAPER_FOOD_INDICATORS

    @property
    def web_scraper_category_patterns(self) -> list[str]:
        """Get category patterns for filtering out category pages."""
        return self.WEB_SCRAPER_CATEGORY_PATTERNS

    @property
    def web_scraper_single_word_categories(self) -> list[str]:
        """Get single-word categories to exclude from recipes."""
        return self.WEB_SCRAPER_SINGLE_WORD_CATEGORIES

    @property
    def web_scraper_category_indicators(self) -> list[str]:
        """Get category indicators for filtering out category pages."""
        return self.WEB_SCRAPER_CATEGORY_INDICATORS


settings = _Settings()
