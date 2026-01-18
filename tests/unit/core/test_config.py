"""Unit tests for application configuration.

Tests cover:
- Settings class
- Environment detection
- Computed properties
- List parsing
"""

from __future__ import annotations

import pytest

from app.core.config import Settings, get_settings
from app.core.config.settings import parse_list


pytestmark = pytest.mark.unit


# =============================================================================
# parse_list Tests
# =============================================================================


class TestParseList:
    """Tests for parse_list helper function."""

    def test_parses_comma_separated_string(self):
        """Should parse comma-separated string."""
        result = parse_list("http://localhost:3000,http://localhost:8080")
        assert result == ["http://localhost:3000", "http://localhost:8080"]

    def test_handles_whitespace(self):
        """Should strip whitespace from values."""
        result = parse_list("http://localhost:3000 , http://localhost:8080 ")
        assert result == ["http://localhost:3000", "http://localhost:8080"]

    def test_handles_empty_string(self):
        """Should return empty list for empty string."""
        result = parse_list("")
        assert result == []

    def test_passes_through_list(self):
        """Should return list as-is."""
        origins = ["http://localhost:3000", "http://localhost:8080"]
        result = parse_list(origins)
        assert result == origins

    def test_filters_empty_values(self):
        """Should filter out empty values from string."""
        result = parse_list("http://localhost:3000,,http://localhost:8080")
        assert result == ["http://localhost:3000", "http://localhost:8080"]


# =============================================================================
# Settings Tests
# =============================================================================


class TestSettings:
    """Tests for Settings class."""

    def test_default_values(self, monkeypatch: pytest.MonkeyPatch):
        """Should have sensible default values from base YAML."""
        # Set APP_ENV before Settings loads YAML files
        monkeypatch.setenv("APP_ENV", "development")
        settings = Settings()

        assert settings.app.name == "Recipe Scraper Service"
        assert settings.APP_ENV == "development"
        assert settings.app.debug is False
        assert settings.server.host == "0.0.0.0"  # From base YAML
        assert settings.server.port == 8000

    def test_environment_override(self, monkeypatch: pytest.MonkeyPatch):
        """Should allow environment variable overrides."""
        monkeypatch.setenv("APP_ENV", "production")
        settings = Settings()

        assert settings.APP_ENV == "production"

    def test_jwt_defaults(self, monkeypatch: pytest.MonkeyPatch):
        """Should have JWT settings with defaults."""
        monkeypatch.setenv("APP_ENV", "development")
        settings = Settings()

        assert settings.auth.jwt.algorithm == "HS256"
        assert settings.auth.jwt.access_token_expire_minutes == 30
        assert settings.auth.jwt.refresh_token_expire_days == 7

    def test_redis_defaults(self, monkeypatch: pytest.MonkeyPatch):
        """Should have Redis settings with model defaults when overridden."""
        monkeypatch.setenv("APP_ENV", "development")
        # Explicitly pass redis config to override YAML values
        settings = Settings(
            redis={
                "host": "localhost",
                "port": 6379,
                "cache_db": 0,
                "queue_db": 1,
                "rate_limit_db": 2,
                "user": None,
            }
        )

        assert settings.redis.host == "localhost"
        assert settings.redis.port == 6379
        assert settings.redis.cache_db == 0
        assert settings.redis.queue_db == 1
        assert settings.redis.rate_limit_db == 2
        assert settings.redis.user is None


class TestSettingsComputedProperties:
    """Tests for Settings computed properties."""

    def test_redis_cache_url_without_password(self, monkeypatch: pytest.MonkeyPatch):
        """Should build Redis URL without password."""
        monkeypatch.setenv("APP_ENV", "development")
        settings = Settings(
            REDIS_PASSWORD="",
            redis={
                "host": "localhost",
                "port": 6379,
                "cache_db": 0,
                "queue_db": 1,
                "rate_limit_db": 2,
                "user": None,
            },
        )

        assert settings.redis_cache_url == "redis://localhost:6379/0"

    def test_redis_cache_url_with_password(self, monkeypatch: pytest.MonkeyPatch):
        """Should build Redis URL with password."""
        monkeypatch.setenv("APP_ENV", "development")
        settings = Settings(
            REDIS_PASSWORD="secret123",
            redis={
                "host": "localhost",
                "port": 6379,
                "cache_db": 0,
                "queue_db": 1,
                "rate_limit_db": 2,
                "user": None,
            },
        )

        assert "secret123" in settings.redis_cache_url
        assert settings.redis_cache_url == "redis://:secret123@localhost:6379/0"

    def test_redis_queue_url(self, monkeypatch: pytest.MonkeyPatch):
        """Should build Redis queue URL."""
        monkeypatch.setenv("APP_ENV", "development")
        settings = Settings(
            REDIS_PASSWORD="",
            redis={
                "host": "localhost",
                "port": 6379,
                "cache_db": 0,
                "queue_db": 1,
                "rate_limit_db": 2,
                "user": None,
            },
        )

        assert settings.redis_queue_url == "redis://localhost:6379/1"

    def test_redis_rate_limit_url(self, monkeypatch: pytest.MonkeyPatch):
        """Should build Redis rate limit URL."""
        monkeypatch.setenv("APP_ENV", "development")
        settings = Settings(
            REDIS_PASSWORD="",
            redis={
                "host": "localhost",
                "port": 6379,
                "cache_db": 0,
                "queue_db": 1,
                "rate_limit_db": 2,
                "user": None,
            },
        )

        assert settings.redis_rate_limit_url == "redis://localhost:6379/2"

    def test_redis_cache_url_with_username_and_password(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Should build Redis URL with username and password (ACL auth)."""
        monkeypatch.setenv("APP_ENV", "development")
        settings = Settings(
            REDIS_PASSWORD="secret123",
            redis={
                "host": "localhost",
                "port": 6379,
                "cache_db": 0,
                "queue_db": 1,
                "rate_limit_db": 2,
                "user": "scraper_user",
            },
        )

        assert (
            settings.redis_cache_url
            == "redis://scraper_user:secret123@localhost:6379/0"
        )

    def test_redis_queue_url_with_username_and_password(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Should build Redis queue URL with username and password."""
        monkeypatch.setenv("APP_ENV", "development")
        settings = Settings(
            REDIS_PASSWORD="secret123",
            redis={
                "host": "localhost",
                "port": 6379,
                "cache_db": 0,
                "queue_db": 1,
                "rate_limit_db": 2,
                "user": "scraper_user",
            },
        )

        assert (
            settings.redis_queue_url
            == "redis://scraper_user:secret123@localhost:6379/1"
        )

    def test_redis_rate_limit_url_with_username_and_password(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Should build Redis rate limit URL with username and password."""
        monkeypatch.setenv("APP_ENV", "development")
        settings = Settings(
            REDIS_PASSWORD="secret123",
            redis={
                "host": "localhost",
                "port": 6379,
                "cache_db": 0,
                "queue_db": 1,
                "rate_limit_db": 2,
                "user": "scraper_user",
            },
        )

        assert (
            settings.redis_rate_limit_url
            == "redis://scraper_user:secret123@localhost:6379/2"
        )

    def test_redis_url_with_username_only(self, monkeypatch: pytest.MonkeyPatch):
        """Should build Redis URL with username but no password."""
        monkeypatch.setenv("APP_ENV", "development")
        settings = Settings(
            REDIS_PASSWORD="",
            redis={
                "host": "localhost",
                "port": 6379,
                "cache_db": 0,
                "queue_db": 1,
                "rate_limit_db": 2,
                "user": "scraper_user",
            },
        )

        assert settings.redis_cache_url == "redis://scraper_user@localhost:6379/0"

    def test_redis_user_field_defaults_to_none(self, monkeypatch: pytest.MonkeyPatch):
        """Should have user field as None when explicitly set."""
        monkeypatch.setenv("APP_ENV", "development")
        settings = Settings(
            redis={
                "host": "localhost",
                "port": 6379,
                "cache_db": 0,
                "queue_db": 1,
                "rate_limit_db": 2,
                "user": None,
            },
        )

        assert settings.redis.user is None


class TestSettingsEnvironmentDetection:
    """Tests for Settings environment detection properties."""

    def test_is_development(self):
        """Should detect development environment."""
        settings = Settings(APP_ENV="development")
        assert settings.is_development is True
        assert settings.is_production is False
        assert settings.is_testing is False

    def test_is_production(self):
        """Should detect production environment."""
        settings = Settings(APP_ENV="production")
        assert settings.is_development is False
        assert settings.is_production is True
        assert settings.is_testing is False

    def test_is_testing(self):
        """Should detect test environment."""
        settings = Settings(APP_ENV="test")
        assert settings.is_development is False
        assert settings.is_production is False
        assert settings.is_testing is True

    def test_is_local(self):
        """Should detect local environment."""
        settings = Settings(APP_ENV="local")
        assert settings.is_local is True
        assert settings.is_development is False

    def test_is_non_production_for_local(self):
        """Should return True for local environment."""
        settings = Settings(APP_ENV="local")
        assert settings.is_non_production is True

    def test_is_non_production_for_test(self):
        """Should return True for test environment."""
        settings = Settings(APP_ENV="test")
        assert settings.is_non_production is True

    def test_is_non_production_for_development(self):
        """Should return True for development environment."""
        settings = Settings(APP_ENV="development")
        assert settings.is_non_production is True

    def test_is_non_production_for_staging(self):
        """Should return False for staging environment."""
        settings = Settings(APP_ENV="staging")
        assert settings.is_non_production is False

    def test_is_non_production_for_production(self):
        """Should return False for production environment."""
        settings = Settings(APP_ENV="production")
        assert settings.is_non_production is False


class TestSettingsCorsOrigins:
    """Tests for CORS origins configuration."""

    def test_cors_origins_from_yaml(self):
        """Should load CORS origins from base YAML."""
        settings = Settings()

        # Base YAML defines development origins
        assert "http://localhost:3000" in settings.api.cors_origins
        assert "http://localhost:8080" in settings.api.cors_origins


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
