"""Settings factory for generating test configurations.

Uses polyfactory for consistent test data generation.
"""

from __future__ import annotations

from polyfactory.factories.pydantic_factory import ModelFactory

from app.core.config import Settings


class SettingsFactory(ModelFactory[Settings]):
    """Factory for generating Settings instances.

    Provides reasonable test defaults for all settings.
    """

    __model__ = Settings

    # Application defaults
    APP_NAME = "Test Recipe Service"
    APP_VERSION = "0.0.1-test"
    ENVIRONMENT = "testing"
    DEBUG = True

    # Server
    HOST = "127.0.0.1"
    PORT = 8000

    # API
    API_V1_PREFIX = "/api/v1"

    # JWT - test values
    JWT_SECRET_KEY = "test-secret-key-minimum-32-characters-long"
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 5
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = 1

    # Service API Keys
    SERVICE_API_KEYS = ["test-api-key"]  # noqa: RUF012

    # CORS
    CORS_ORIGINS = ["http://localhost:3000"]  # noqa: RUF012

    # Redis
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_PASSWORD = ""
    REDIS_CACHE_DB = 0
    REDIS_QUEUE_DB = 1
    REDIS_RATE_LIMIT_DB = 2
    CLIENT_CACHE_MAX_AGE = 30

    # Rate limiting
    RATE_LIMIT_DEFAULT = "1000/minute"
    RATE_LIMIT_AUTH = "100/minute"

    # Logging
    LOG_LEVEL = "DEBUG"
    LOG_FORMAT = "text"

    # Observability - disabled for tests
    OTLP_ENDPOINT = None
    ENABLE_TRACING = False
    METRICS_ENABLED = False
    SENTRY_DSN = None

    # Feature flags
    FEATURE_FLAGS_ENABLED = False

    @classmethod
    def development(cls) -> Settings:
        """Create settings for development environment."""
        return cls.build(ENVIRONMENT="development", DEBUG=True)

    @classmethod
    def production(cls) -> Settings:
        """Create settings for production environment."""
        return cls.build(
            ENVIRONMENT="production",
            DEBUG=False,
            LOG_FORMAT="json",
            ENABLE_TRACING=True,
            METRICS_ENABLED=True,
        )

    @classmethod
    def with_redis(cls, host: str = "localhost", port: int = 6379) -> Settings:
        """Create settings with specific Redis configuration."""
        return cls.build(REDIS_HOST=host, REDIS_PORT=port)
