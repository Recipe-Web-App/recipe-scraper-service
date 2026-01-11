"""Application configuration using Pydantic Settings.

This module provides centralized configuration management with:
- Environment variable loading
- Type validation and coercion
- Computed properties for derived values
- Caching for performance
"""

from enum import StrEnum
from functools import lru_cache
from typing import Annotated

from pydantic import BeforeValidator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthMode(StrEnum):
    """Authentication mode configuration.

    Determines how tokens are validated:
    - INTROSPECTION: Validate via external auth-service /oauth2/introspect
    - LOCAL_JWT: Validate JWTs locally using shared secret
    - HEADER: Extract user from X-User-ID header (testing/development only)
    - DISABLED: No authentication required
    """

    INTROSPECTION = "introspection"
    LOCAL_JWT = "local_jwt"
    HEADER = "header"
    DISABLED = "disabled"


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
    # External Auth Service Configuration
    # =========================================================================
    # Auth mode: introspection, local_jwt, header, disabled
    AUTH_MODE: str = "local_jwt"

    # External auth service base URL (required for introspection mode)
    AUTH_SERVICE_URL: str | None = None

    # OAuth2 client credentials for token introspection
    AUTH_SERVICE_CLIENT_ID: str | None = None
    AUTH_SERVICE_CLIENT_SECRET: str | None = None

    # Token introspection settings
    AUTH_INTROSPECTION_CACHE_TTL: int = 60  # seconds to cache introspection results
    AUTH_INTROSPECTION_TIMEOUT: float = 5.0  # HTTP timeout in seconds

    # Fallback to local JWT validation when introspection fails
    AUTH_INTROSPECTION_FALLBACK_LOCAL: bool = False

    # Header-based auth settings (for testing/development)
    AUTH_HEADER_USER_ID: str = "X-User-ID"
    AUTH_HEADER_ROLES: str = "X-User-Roles"
    AUTH_HEADER_PERMISSIONS: str = "X-User-Permissions"

    # JWT validation settings (for local_jwt mode and introspection fallback)
    AUTH_JWT_ISSUER: str | None = None  # Expected issuer claim
    AUTH_JWT_AUDIENCE: Annotated[list[str], BeforeValidator(parse_cors)] = []

    @property
    def auth_mode_enum(self) -> AuthMode:
        """Get auth mode as enum with validation."""
        try:
            return AuthMode(self.AUTH_MODE.lower())
        except ValueError:
            msg = (
                f"Invalid AUTH_MODE: {self.AUTH_MODE}. "
                f"Must be one of: {', '.join(m.value for m in AuthMode)}"
            )
            raise ValueError(msg) from None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def AUTH_SERVICE_INTROSPECTION_URL(self) -> str | None:
        """Full introspection endpoint URL."""
        if self.AUTH_SERVICE_URL:
            return f"{self.AUTH_SERVICE_URL.rstrip('/')}/oauth2/introspect"
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def AUTH_SERVICE_USERINFO_URL(self) -> str | None:
        """Full userinfo endpoint URL."""
        if self.AUTH_SERVICE_URL:
            return f"{self.AUTH_SERVICE_URL.rstrip('/')}/oauth2/userinfo"
        return None

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
