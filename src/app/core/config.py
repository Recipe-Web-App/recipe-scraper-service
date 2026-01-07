"""Application configuration using Pydantic Settings.

This module provides centralized configuration management with:
- Environment variable loading
- Type validation and coercion
- Computed properties for derived values
- Caching for performance
"""

from functools import lru_cache
from typing import Annotated

from pydantic import BeforeValidator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors(v: str | list[str]) -> list[str]:
    """Parse CORS origins from comma-separated string or list."""
    if isinstance(v, str):
        return [origin.strip() for origin in v.split(",") if origin.strip()]
    return v


class Settings(BaseSettings):
    """Application settings with environment variable support.

    All settings can be overridden via environment variables.
    Environment variables take precedence over .env file values.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=False,
    )

    # =========================================================================
    # Application
    # =========================================================================
    APP_NAME: str = "Recipe Scraper Service"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # =========================================================================
    # API
    # =========================================================================
    API_V1_PREFIX: str = "/api/v1"

    # =========================================================================
    # Security / JWT
    # =========================================================================
    JWT_SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Service API Keys for service-to-service auth (comma-separated)
    SERVICE_API_KEYS: Annotated[list[str], BeforeValidator(parse_cors)] = []

    # CORS
    CORS_ORIGINS: Annotated[list[str], BeforeValidator(parse_cors)] = []

    # =========================================================================
    # Redis Cache
    # =========================================================================
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    # Cache DB
    REDIS_CACHE_DB: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_CACHE_URL(self) -> str:
        """Build Redis cache connection URL."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_CACHE_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_CACHE_DB}"

    CLIENT_CACHE_MAX_AGE: int = 30

    # =========================================================================
    # Redis Queue (ARQ)
    # =========================================================================
    REDIS_QUEUE_DB: int = 1

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_QUEUE_URL(self) -> str:
        """Build Redis queue connection URL for ARQ."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_QUEUE_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_QUEUE_DB}"

    # =========================================================================
    # Redis Rate Limiting
    # =========================================================================
    REDIS_RATE_LIMIT_DB: int = 2

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_RATE_LIMIT_URL(self) -> str:
        """Build Redis rate limit connection URL."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_RATE_LIMIT_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_RATE_LIMIT_DB}"

    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_AUTH: str = "5/minute"

    # =========================================================================
    # Logging
    # =========================================================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text

    # =========================================================================
    # Observability
    # =========================================================================
    OTLP_ENDPOINT: str | None = None
    ENABLE_TRACING: bool = True
    METRICS_ENABLED: bool = True
    SENTRY_DSN: str | None = None

    # =========================================================================
    # Feature Flags
    # =========================================================================
    FEATURE_FLAGS_ENABLED: bool = True

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.ENVIRONMENT == "testing"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Using lru_cache ensures settings are only loaded once,
    improving performance and consistency.
    """
    return Settings()


# Global settings instance for convenient imports
settings = get_settings()
