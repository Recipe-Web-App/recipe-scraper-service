"""Application configuration using Pydantic Settings with YAML support.

This module provides centralized configuration management with:
- YAML-based configuration files organized by domain
- Environment-specific overrides (local, test, development, staging, production)
- Environment variable loading for secrets
- Type validation and coercion
- Computed properties for derived values
- Caching for performance
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .yaml_source import MultiYamlConfigSettingsSource


if TYPE_CHECKING:
    from pydantic_settings import PydanticBaseSettingsSource


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


def parse_list(v: str | list[str]) -> list[str]:
    """Parse comma-separated string or list into list of strings."""
    if isinstance(v, str):
        return [x.strip() for x in v.split(",") if x.strip()]
    return v


# =============================================================================
# Nested Configuration Models (from YAML)
# =============================================================================


class AppSettings(BaseModel):
    """Application identity settings."""

    name: str = "Recipe Scraper Service"
    version: str = "0.1.0"
    debug: bool = False


class ServerSettings(BaseModel):
    """Server configuration settings."""

    host: str = "127.0.0.1"
    port: int = 8000


class ApiSettings(BaseModel):
    """API configuration settings."""

    v1_prefix: str = "/api/v1/recipe-scraper"
    cors_origins: list[str] = []


class JwtSettings(BaseModel):
    """JWT token settings."""

    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7


class AuthIntrospectionSettings(BaseModel):
    """Token introspection settings."""

    cache_ttl: int = 60
    timeout: float = 5.0
    fallback_local: bool = False


class AuthHeaderSettings(BaseModel):
    """Header-based auth settings."""

    user_id: str = "X-User-ID"
    roles: str = "X-User-Roles"
    permissions: str = "X-User-Permissions"


class AuthServiceSettings(BaseModel):
    """External auth service settings."""

    url: str | None = None
    client_id: str | None = None


class AuthJwtValidationSettings(BaseModel):
    """JWT validation settings."""

    issuer: str | None = None
    audience: list[str] = []


class AuthSettings(BaseModel):
    """Authentication configuration settings."""

    mode: str = "local_jwt"
    jwt: JwtSettings = JwtSettings()
    introspection: AuthIntrospectionSettings = AuthIntrospectionSettings()
    headers: AuthHeaderSettings = AuthHeaderSettings()
    service: AuthServiceSettings = AuthServiceSettings()
    jwt_validation: AuthJwtValidationSettings = AuthJwtValidationSettings()


class RedisSettings(BaseModel):
    """Redis configuration settings."""

    host: str = "localhost"
    port: int = 6379
    user: str | None = None  # Redis ACL username (Redis 6.0+)
    cache_db: int = 0
    queue_db: int = 1
    rate_limit_db: int = 2
    client_cache_max_age: int = 30


class DatabaseSettings(BaseModel):
    """PostgreSQL database configuration settings."""

    host: str = "localhost"
    port: int = 5432
    name: str = "recipe_database"
    db_schema: str = "recipe_manager"  # PostgreSQL schema
    user: str | None = None  # PostgreSQL username
    min_pool_size: int = 5  # Minimum connections in pool
    max_pool_size: int = 20  # Maximum connections in pool
    command_timeout: float = 30.0  # Query timeout in seconds
    ssl: bool = False  # Enable SSL connection


class RateLimitingSettings(BaseModel):
    """Rate limiting configuration."""

    default: str = "100/minute"
    auth: str = "5/minute"


class LoggingSettings(BaseModel):
    """Logging configuration settings."""

    level: str = "INFO"
    format: str = "json"


class TracingSettings(BaseModel):
    """Tracing configuration settings."""

    enabled: bool = True
    otlp_endpoint: str | None = None


class MetricsSettings(BaseModel):
    """Metrics configuration settings."""

    enabled: bool = True


class ObservabilitySettings(BaseModel):
    """Observability configuration settings."""

    tracing: TracingSettings = TracingSettings()
    metrics: MetricsSettings = MetricsSettings()


class OllamaSettings(BaseModel):
    """Ollama LLM service configuration."""

    url: str = "http://localhost:11434"
    model: str = "mistral:7b"
    timeout: float = 60.0
    max_retries: int = 2


class GroqSettings(BaseModel):
    """Groq LLM service configuration."""

    url: str = "https://api.groq.com/openai/v1"
    model: str = "llama-3.1-8b-instant"
    timeout: float = 30.0
    max_retries: int = 2
    requests_per_minute: float = 30.0  # Groq free tier rate limit


class LLMFallbackSettings(BaseModel):
    """LLM fallback behavior configuration."""

    enabled: bool = True
    secondary_provider: str = "groq"


class LLMCacheSettings(BaseModel):
    """LLM response caching configuration."""

    enabled: bool = True
    ttl: int = 3600


class LLMSettings(BaseModel):
    """LLM configuration settings."""

    enabled: bool = True
    provider: str = "ollama"
    ollama: OllamaSettings = OllamaSettings()
    groq: GroqSettings = GroqSettings()
    fallback: LLMFallbackSettings = LLMFallbackSettings()
    cache: LLMCacheSettings = LLMCacheSettings()


class FeaturesSettings(BaseModel):
    """Feature flags configuration."""

    flags_enabled: bool = True


class PopularRecipeScoringSettings(BaseModel):
    """Weights for the popularity scoring algorithm.

    These weights determine how different engagement metrics contribute
    to the final popularity score. Weights are redistributed proportionally
    when metrics are missing for a recipe.
    """

    rating_weight: float = 0.35  # Weight for star rating (0-5 scale)
    rating_count_weight: float = 0.25  # Weight for number of ratings
    favorites_weight: float = 0.25  # Weight for favorites/saves
    reviews_weight: float = 0.10  # Weight for review count
    position_weight: float = 0.05  # Weight for position on page (rank)


class PopularRecipeSourceSettings(BaseModel):
    """Configuration for a single popular recipe source."""

    name: str  # Human-readable name (e.g., "AllRecipes")
    base_url: str  # Base URL for the website
    popular_endpoint: str  # Path to popular/trending page
    enabled: bool = True
    max_recipes: int = 100  # Max recipes to fetch from this source
    source_weight: float = 1.0  # Base weight for this source (0-1)


class PopularRecipesSettings(BaseModel):
    """Popular recipes aggregation configuration."""

    enabled: bool = True
    cache_ttl: int = 86400  # 24 hours
    cache_key: str = "popular_recipes"
    refresh_threshold: int = 3600  # Refresh when TTL < 1 hour
    target_total: int = 500  # Target ~500 recipes total
    fetch_timeout: float = 30.0
    max_concurrent_fetches: int = 5
    sources: list[PopularRecipeSourceSettings] = []
    scoring: PopularRecipeScoringSettings = PopularRecipeScoringSettings()

    # LLM-based extraction settings
    use_llm_extraction: bool = True  # Enable LLM-based recipe link extraction
    llm_extraction_max_html_chars: int = 32000  # Max HTML size per batch (~8K tokens)
    llm_extraction_min_confidence: float = 0.5  # Min confidence to include a link
    llm_extraction_chunk_size: int = 50  # Links per LLM batch

    # Limit control: fetch metrics for up to this many links per source
    max_links_to_process: int = 100


class ScrapingSettings(BaseModel):
    """Recipe scraping configuration."""

    fetch_timeout: float = 30.0
    max_retries: int = 2
    cache_enabled: bool = True
    cache_ttl: int = 86400  # 24 hours
    cache_max_items: int = 1000
    popular_recipes: PopularRecipesSettings = PopularRecipesSettings()


class RecipeManagementServiceSettings(BaseModel):
    """Recipe Management Service client configuration."""

    url: str | None = None
    timeout: float = 10.0
    max_retries: int = 2


class DownstreamServicesSettings(BaseModel):
    """Configuration for downstream service clients."""

    recipe_management: RecipeManagementServiceSettings = (
        RecipeManagementServiceSettings()
    )


class ArqJobIdsSettings(BaseModel):
    """Centralized job IDs for ARQ background tasks.

    Using fixed IDs enables job deduplication - if a job with the same ID
    is already queued or in-progress, a new one won't be created.
    """

    popular_recipes_refresh: str = "popular_recipes_refresh"


class ArqSettings(BaseModel):
    """ARQ background worker configuration."""

    job_ids: ArqJobIdsSettings = ArqJobIdsSettings()
    queue_name: str = "scraper:queue:jobs"
    health_check_key: str = "scraper:queue:health-check"


# =============================================================================
# Main Settings Class
# =============================================================================


class Settings(BaseSettings):
    """Application settings with YAML + environment variable support.

    Configuration is loaded from multiple sources with the following priority
    (highest to lowest):
    1. Environment variables
    2. .env file (secrets only)
    3. Environment-specific YAML files (config/environments/{APP_ENV}/)
    4. Base YAML files (config/base/)
    5. Default values in code

    Environment variables can override any setting using the nested delimiter '__'.
    For example: REDIS__HOST=prod-redis overrides redis.host.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=False,
        env_nested_delimiter="__",
    )

    # =========================================================================
    # Environment Selection (from .env)
    # =========================================================================
    APP_ENV: str = "development"

    # =========================================================================
    # Nested Configuration Sections (from YAML)
    # =========================================================================
    app: AppSettings = AppSettings()
    server: ServerSettings = ServerSettings()
    api: ApiSettings = ApiSettings()
    auth: AuthSettings = AuthSettings()
    redis: RedisSettings = RedisSettings()
    database: DatabaseSettings = DatabaseSettings()
    rate_limiting: RateLimitingSettings = RateLimitingSettings()
    logging: LoggingSettings = LoggingSettings()
    observability: ObservabilitySettings = ObservabilitySettings()
    features: FeaturesSettings = FeaturesSettings()
    llm: LLMSettings = LLMSettings()
    scraping: ScrapingSettings = ScrapingSettings()
    downstream_services: DownstreamServicesSettings = DownstreamServicesSettings()
    arq: ArqSettings = ArqSettings()

    # =========================================================================
    # Secrets (from .env only - never in YAML)
    # =========================================================================
    JWT_SECRET_KEY: str = ""
    REDIS_PASSWORD: str = ""
    DATABASE_PASSWORD: str = ""
    AUTH_SERVICE_CLIENT_SECRET: str | None = None
    SENTRY_DSN: str | None = None
    GROQ_API_KEY: str = ""

    # Service API Keys for service-to-service auth (comma-separated in .env)
    SERVICE_API_KEYS: Annotated[list[str], BeforeValidator(parse_list)] = []

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customize settings loading order.

        Priority (highest to lowest):
        1. init_settings - Values passed to Settings()
        2. env_settings - Environment variables
        3. dotenv_settings - .env file (secrets)
        4. yaml_settings - YAML files (base + environment)
        5. file_secret_settings - Docker secrets
        """
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            MultiYamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )

    # =========================================================================
    # Computed Fields
    # =========================================================================

    @property
    def auth_mode_enum(self) -> AuthMode:
        """Get auth mode as enum with validation."""
        try:
            return AuthMode(self.auth.mode.lower())
        except ValueError:
            msg = (
                f"Invalid auth mode: {self.auth.mode}. "
                f"Must be one of: {', '.join(m.value for m in AuthMode)}"
            )
            raise ValueError(msg) from None

    @property
    def auth_service_introspection_url(self) -> str | None:
        """Full introspection endpoint URL."""
        if self.auth.service.url:
            return f"{self.auth.service.url.rstrip('/')}/oauth2/introspect"
        return None

    @property
    def auth_service_userinfo_url(self) -> str | None:
        """Full userinfo endpoint URL."""
        if self.auth.service.url:
            return f"{self.auth.service.url.rstrip('/')}/oauth2/userinfo"
        return None

    def _build_redis_url(self, db: int) -> str:
        """Build Redis connection URL with optional authentication.

        Supports Redis 6.0+ ACL authentication with username.
        URL format: redis://[user:password@]host:port/db

        Args:
            db: Redis database number

        Returns:
            Redis connection URL string
        """
        auth_part = ""
        if self.redis.user and self.REDIS_PASSWORD:
            auth_part = f"{self.redis.user}:{self.REDIS_PASSWORD}@"
        elif self.REDIS_PASSWORD:
            auth_part = f":{self.REDIS_PASSWORD}@"
        elif self.redis.user:
            auth_part = f"{self.redis.user}@"

        return f"redis://{auth_part}{self.redis.host}:{self.redis.port}/{db}"

    @property
    def redis_cache_url(self) -> str:
        """Build Redis cache connection URL."""
        return self._build_redis_url(self.redis.cache_db)

    @property
    def redis_queue_url(self) -> str:
        """Build Redis queue connection URL for ARQ."""
        return self._build_redis_url(self.redis.queue_db)

    @property
    def redis_rate_limit_url(self) -> str:
        """Build Redis rate limit connection URL."""
        return self._build_redis_url(self.redis.rate_limit_db)

    @property
    def database_url(self) -> str:
        """Build PostgreSQL connection URL.

        URL format: postgresql://[user:password@]host:port/database

        Returns:
            PostgreSQL connection URL string
        """
        auth_part = ""
        if self.database.user and self.DATABASE_PASSWORD:
            auth_part = f"{self.database.user}:{self.DATABASE_PASSWORD}@"
        elif self.database.user:
            auth_part = f"{self.database.user}@"

        return (
            f"postgresql://{auth_part}{self.database.host}:"
            f"{self.database.port}/{self.database.name}"
        )

    # =========================================================================
    # Environment Helpers
    # =========================================================================

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.APP_ENV == "production"

    @property
    def is_non_production(self) -> bool:
        """Check if running in a non-production environment.

        Returns True for local, test, and development environments where
        features like API documentation, debug logging, and detailed error
        messages should be enabled.
        """
        return self.APP_ENV in ("local", "test", "development")

    @property
    def is_testing(self) -> bool:
        """Check if running in test environment."""
        return self.APP_ENV == "test"

    @property
    def is_local(self) -> bool:
        """Check if running in local environment."""
        return self.APP_ENV == "local"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Using lru_cache ensures settings are only loaded once,
    improving performance and consistency.
    """
    return Settings()


# Global settings instance for convenient imports
settings = get_settings()
