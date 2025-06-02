"""Application configuration settings.

Defines and loads configuration variables and settings used across the application,
including environment-specific and default configurations.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class _Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file.

    This class encapsulates all configuration required for the application, including
    database connection details. All fields are private and accessed via read-only
    properties.
    """

    _POSTGRES_HOST: str = Field(..., alias="POSTGRES_HOST")
    _POSTGRES_PORT: int = Field(..., alias="POSTGRES_PORT")
    _POSTGRES_DB: str = Field(..., alias="POSTGRES_DB")
    _POSTGRES_SCHEMA: str = Field(..., alias="POSTGRES_SCHEMA")
    _RECIPE_SCRAPER_DB_USER: str = Field(..., alias="RECIPE_SCRAPER_DB_USER")
    _RECIPE_SCRAPER_DB_PASSWORD: str = Field(..., alias="RECIPE_SCRAPER_DB_PASSWORD")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        validate_default=True,
    )

    @property
    def postgres_host(self) -> str:
        """Database host address.

        Returns:
            str: Hostname or IP address of the PostgreSQL server.
        """
        return self._POSTGRES_HOST

    @property
    def postgres_port(self) -> int:
        """Database port number.

        Returns:
            int: Port number on which the PostgreSQL server is listening.
        """
        return self._POSTGRES_PORT

    @property
    def postgres_db(self) -> str:
        """Database name.

        Returns:
            str: Name of the PostgreSQL database to connect to.
        """
        return self._POSTGRES_DB

    @property
    def postgres_schema(self) -> str:
        """Database schema name.

        Returns:
            str: Name of the PostgreSQL schema to use.
        """
        return self._POSTGRES_SCHEMA

    @property
    def recipe_scraper_db_user(self) -> str:
        """Database user for the recipe scraper service.

        Returns:
            str: Username for authenticating with the PostgreSQL database.
        """
        return self._RECIPE_SCRAPER_DB_USER

    @property
    def recipe_scraper_db_password(self) -> str:
        """Database password for the recipe scraper service.

        Returns:
            str: Password for authenticating with the PostgreSQL database.
        """
        return self._RECIPE_SCRAPER_DB_PASSWORD


settings = _Settings()
