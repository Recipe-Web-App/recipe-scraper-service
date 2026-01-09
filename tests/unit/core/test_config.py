"""Unit tests for application configuration.

Tests cover:
- Settings class
- Environment detection
- Computed properties
- CORS/API key parsing
"""

from __future__ import annotations

import pytest

from app.core.config import Settings, get_settings, parse_cors


pytestmark = pytest.mark.unit


# =============================================================================
# parse_cors Tests
# =============================================================================


class TestParseCors:
    """Tests for parse_cors helper function."""

    def test_parses_comma_separated_string(self):
        """Should parse comma-separated origins string."""
        result = parse_cors("http://localhost:3000,http://localhost:8080")
        assert result == ["http://localhost:3000", "http://localhost:8080"]

    def test_handles_whitespace(self):
        """Should strip whitespace from origins."""
        result = parse_cors("http://localhost:3000 , http://localhost:8080 ")
        assert result == ["http://localhost:3000", "http://localhost:8080"]

    def test_handles_empty_string(self):
        """Should return empty list for empty string."""
        result = parse_cors("")
        assert result == []

    def test_passes_through_list(self):
        """Should return list as-is."""
        origins = ["http://localhost:3000", "http://localhost:8080"]
        result = parse_cors(origins)
        assert result == origins

    def test_filters_empty_values(self):
        """Should filter out empty values from string."""
        result = parse_cors("http://localhost:3000,,http://localhost:8080")
        assert result == ["http://localhost:3000", "http://localhost:8080"]


# =============================================================================
# Settings Tests
# =============================================================================


class TestSettings:
    """Tests for Settings class."""

    def test_default_values(self):
        """Should have sensible default values."""
        settings = Settings()

        assert settings.APP_NAME == "Recipe Scraper Service"
        assert settings.ENVIRONMENT == "development"
        assert settings.DEBUG is False
        assert settings.HOST == "0.0.0.0"
        assert settings.PORT == 8000

    def test_environment_override(self):
        """Should allow environment variable overrides."""
        settings = Settings(ENVIRONMENT="production", DEBUG=True)

        assert settings.ENVIRONMENT == "production"
        assert settings.DEBUG is True

    def test_jwt_defaults(self):
        """Should have JWT settings with defaults."""
        settings = Settings()

        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS == 7

    def test_redis_defaults(self):
        """Should have Redis settings with defaults."""
        settings = Settings()

        assert settings.REDIS_HOST == "localhost"
        assert settings.REDIS_PORT == 6379
        assert settings.REDIS_CACHE_DB == 0
        assert settings.REDIS_QUEUE_DB == 1
        assert settings.REDIS_RATE_LIMIT_DB == 2


class TestSettingsComputedProperties:
    """Tests for Settings computed properties."""

    def test_redis_cache_url_without_password(self):
        """Should build Redis URL without password."""
        settings = Settings(
            REDIS_HOST="localhost",
            REDIS_PORT=6379,
            REDIS_PASSWORD="",
            REDIS_CACHE_DB=0,
        )

        assert settings.REDIS_CACHE_URL == "redis://localhost:6379/0"

    def test_redis_cache_url_with_password(self):
        """Should build Redis URL with password."""
        settings = Settings(
            REDIS_HOST="redis.example.com",
            REDIS_PORT=6380,
            REDIS_PASSWORD="secret123",
            REDIS_CACHE_DB=2,
        )

        assert settings.REDIS_CACHE_URL == "redis://:secret123@redis.example.com:6380/2"

    def test_redis_queue_url(self):
        """Should build Redis queue URL."""
        settings = Settings(
            REDIS_HOST="localhost",
            REDIS_PORT=6379,
            REDIS_PASSWORD="",
            REDIS_QUEUE_DB=1,
        )

        assert settings.REDIS_QUEUE_URL == "redis://localhost:6379/1"

    def test_redis_rate_limit_url(self):
        """Should build Redis rate limit URL."""
        settings = Settings(
            REDIS_HOST="localhost",
            REDIS_PORT=6379,
            REDIS_PASSWORD="",
            REDIS_RATE_LIMIT_DB=2,
        )

        assert settings.REDIS_RATE_LIMIT_URL == "redis://localhost:6379/2"


class TestSettingsEnvironmentDetection:
    """Tests for Settings environment detection properties."""

    def test_is_development(self):
        """Should detect development environment."""
        settings = Settings(ENVIRONMENT="development")
        assert settings.is_development is True
        assert settings.is_production is False
        assert settings.is_testing is False

    def test_is_production(self):
        """Should detect production environment."""
        settings = Settings(ENVIRONMENT="production")
        assert settings.is_development is False
        assert settings.is_production is True
        assert settings.is_testing is False

    def test_is_testing(self):
        """Should detect testing environment."""
        settings = Settings(ENVIRONMENT="testing")
        assert settings.is_development is False
        assert settings.is_production is False
        assert settings.is_testing is True


class TestSettingsCorsOrigins:
    """Tests for CORS origins configuration."""

    def test_parses_cors_from_string(self):
        """Should parse CORS origins from comma-separated string."""
        settings = Settings(CORS_ORIGINS="http://localhost:3000,http://localhost:8080")

        assert settings.CORS_ORIGINS == [
            "http://localhost:3000",
            "http://localhost:8080",
        ]

    def test_accepts_cors_as_list(self):
        """Should accept CORS origins as list."""
        settings = Settings(CORS_ORIGINS=["http://localhost:3000"])

        assert settings.CORS_ORIGINS == ["http://localhost:3000"]

    def test_empty_cors_default(self):
        """Should default to empty CORS origins."""
        settings = Settings()

        assert settings.CORS_ORIGINS == []


class TestSettingsServiceApiKeys:
    """Tests for service API keys configuration."""

    def test_parses_api_keys_from_string(self):
        """Should parse API keys from comma-separated string."""
        settings = Settings(SERVICE_API_KEYS="key1,key2,key3")

        assert settings.SERVICE_API_KEYS == ["key1", "key2", "key3"]

    def test_accepts_api_keys_as_list(self):
        """Should accept API keys as list."""
        settings = Settings(SERVICE_API_KEYS=["key1", "key2"])

        assert settings.SERVICE_API_KEYS == ["key1", "key2"]

    def test_empty_api_keys_default(self):
        """Should default to empty API keys."""
        settings = Settings()

        assert settings.SERVICE_API_KEYS == []


# =============================================================================
# get_settings Tests
# =============================================================================


class TestGetSettings:
    """Tests for get_settings function."""

    def test_returns_settings_instance(self):
        """Should return a Settings instance."""
        # Clear the cache first
        get_settings.cache_clear()

        settings = get_settings()

        assert isinstance(settings, Settings)

    def test_returns_cached_instance(self):
        """Should return the same cached instance."""
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_cache_can_be_cleared(self):
        """Should allow cache clearing for testing."""
        get_settings.cache_clear()

        settings1 = get_settings()
        get_settings.cache_clear()
        settings2 = get_settings()

        # After clearing, should get a new instance
        # (though with same defaults, they'll be equal but not identical)
        assert settings1 is not settings2
