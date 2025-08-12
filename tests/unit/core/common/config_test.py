"""Unit tests for the application config module (config.py)."""

import io
import json
from unittest.mock import mock_open, patch

import pytest

import app.core.config.config as config_mod

MOCK_LOGGING_PATH = "/mock/logging.json"
MOCK_RECIPES_PATH = "/mock/recipes.json"
MOCK_WEBSCRAPER_PATH = "/mock/webscraper.yaml"
MOCK_POSTGRES_PORT = 1234
MOCK_DB_PASSWORD = "mock-password"  # noqa: S105 # pragma: allowlist secret


@pytest.mark.unit
def test_settings_env_and_properties(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that all required env vars and config files are loaded and mapped."""
    # Arrange
    env_vars = {
        "POSTGRES_HOST": "mock-host",
        "POSTGRES_PORT": str(MOCK_POSTGRES_PORT),
        "POSTGRES_DB": "mock-db",
        "POSTGRES_SCHEMA": "mock-schema",
        "RECIPE_SCRAPER_DB_USER": "mock-user",
        "RECIPE_SCRAPER_DB_PASSWORD": MOCK_DB_PASSWORD,
        "SPOONACULAR_API_KEY": "mock-apikey",  # pragma: allowlist secret
        "LOGGING_CONFIG_PATH": MOCK_LOGGING_PATH,
        "POPULAR_RECIPES_CONFIG_PATH": MOCK_RECIPES_PATH,
        "WEB_SCRAPER_CONFIG_PATH": MOCK_WEBSCRAPER_PATH,
    }
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)

    mock_logging_json = json.dumps(
        {
            "sinks": [
                {"sink": "sys.stdout", "level": "INFO"},
                {"sink": "app.log", "level": "DEBUG"},
            ],
        },
    )
    mock_recipes_json = '["https://mock-url-1.com", "https://mock-url-2.com"]'
    mock_webscraper_yaml = """
nav_prefixes: ["/recipes", "/blog"]
url_exclude_keywords: ["ads", "promo"]
exclude_names: ["Test"]
food_indicators: ["food", "dish"]
category_patterns: ["cat1", "cat2"]
single_word_categories: ["cat"]
category_indicators: ["main", "side"]
"""
    m = mock_open()
    m.side_effect = [
        mock_open(read_data=mock_logging_json).return_value,
        mock_open(read_data=mock_recipes_json).return_value,
        mock_open(read_data=mock_webscraper_yaml).return_value,
    ]

    # Path-aware mock for Path.open
    def path_open_side_effect(
        self: object,
        *args: object,  # noqa: ARG001
        **kwargs: object,  # noqa: ARG001
    ) -> object:
        if str(self).endswith("logging.json"):
            return io.StringIO(mock_logging_json)
        if str(self).endswith("recipes.json"):
            return io.StringIO(mock_recipes_json)
        if str(self).endswith("webscraper.yaml"):
            return io.StringIO(mock_webscraper_yaml)
        msg = f"Unexpected file: {self}"
        raise FileNotFoundError(msg)

    with (
        patch("builtins.open", m),
        patch("pathlib.Path.open", path_open_side_effect),
        patch(
            "yaml.safe_load",
            return_value={
                "nav_prefixes": ["/recipes", "/blog"],
                "url_exclude_keywords": ["ads", "promo"],
                "exclude_names": ["Test"],
                "food_indicators": ["food", "dish"],
                "category_patterns": ["cat1", "cat2"],
                "single_word_categories": ["cat"],
                "category_indicators": ["main", "side"],
            },
        ),
    ):
        # Direct instantiation of _Settings is intentional for test coverage.
        s = config_mod._Settings()  # noqa: SLF001

    # Assert
    assert s.POSTGRES_HOST == "mock-host"
    assert s.POSTGRES_PORT in {MOCK_POSTGRES_PORT, str(MOCK_POSTGRES_PORT)}
    assert s.POSTGRES_DB == "mock-db"
    assert s.POSTGRES_SCHEMA == "mock-schema"
    assert s.RECIPE_SCRAPER_DB_USER == "mock-user"
    assert s.RECIPE_SCRAPER_DB_PASSWORD == MOCK_DB_PASSWORD
    assert s.SPOONACULAR_API_KEY == "mock-apikey"  # pragma: allowlist secret
    assert s.LOGGING_CONFIG_PATH == MOCK_LOGGING_PATH
    assert s.POPULAR_RECIPES_CONFIG_PATH == MOCK_RECIPES_PATH
    assert s.WEB_SCRAPER_CONFIG_PATH == MOCK_WEBSCRAPER_PATH
    assert s.POPULAR_RECIPE_URLS == ["https://mock-url-1.com", "https://mock-url-2.com"]
    assert s.WEB_SCRAPER_NAV_PREFIXES == ["/recipes", "/blog"]
    assert s.WEB_SCRAPER_URL_EXCLUDE_KEYWORDS == ["ads", "promo"]
    assert s.WEB_SCRAPER_EXCLUDE_NAMES == ["Test"]
    assert s.WEB_SCRAPER_FOOD_INDICATORS == ["food", "dish"]
    assert s.WEB_SCRAPER_CATEGORY_PATTERNS == ["cat1", "cat2"]
    assert s.WEB_SCRAPER_SINGLE_WORD_CATEGORIES == ["cat"]
    assert s.WEB_SCRAPER_CATEGORY_INDICATORS == ["main", "side"]
    assert hasattr(s, "logging_sinks")
    assert any(sink.sink == "sys.stdout" for sink in s.logging_sinks)
    assert any(
        isinstance(sink.sink, str) and sink.sink.endswith(".log")
        for sink in s.logging_sinks
    )


@pytest.mark.unit
def test_settings_property_methods(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test all property methods for correct values and types."""
    # Arrange
    monkeypatch.setattr(config_mod, "settings", config_mod._Settings())  # noqa: SLF001
    s = config_mod.settings
    # Act & Assert
    assert s.postgres_host == s.POSTGRES_HOST
    assert s.postgres_port == s.POSTGRES_PORT
    assert s.postgres_db == s.POSTGRES_DB
    assert s.postgres_schema == s.POSTGRES_SCHEMA
    assert s.recipe_scraper_db_user == s.RECIPE_SCRAPER_DB_USER
    assert s.recipe_scraper_db_password == s.RECIPE_SCRAPER_DB_PASSWORD
    assert s.popular_recipe_urls == s.POPULAR_RECIPE_URLS
    assert isinstance(s.logging_sinks, list)
    assert s.spoonacular_api_key == s.SPOONACULAR_API_KEY
    assert s.web_scraper_nav_prefixes == s.WEB_SCRAPER_NAV_PREFIXES
    assert s.web_scraper_url_exclude_keywords == s.WEB_SCRAPER_URL_EXCLUDE_KEYWORDS
    assert s.web_scraper_exclude_names == s.WEB_SCRAPER_EXCLUDE_NAMES
    assert s.web_scraper_food_indicators == s.WEB_SCRAPER_FOOD_INDICATORS
    assert s.web_scraper_category_patterns == s.WEB_SCRAPER_CATEGORY_PATTERNS
    assert s.web_scraper_single_word_categories == s.WEB_SCRAPER_SINGLE_WORD_CATEGORIES
    assert s.web_scraper_category_indicators == s.WEB_SCRAPER_CATEGORY_INDICATORS


@pytest.mark.unit
def test_logging_sink_properties() -> None:
    """Test logging_stdout_sink and logging_file_sink properties."""
    # Arrange
    s = config_mod._Settings()  # noqa: SLF001
    # Act
    stdout_sink = s.logging_stdout_sink
    file_sink = s.logging_file_sink
    # Assert
    assert stdout_sink is None or stdout_sink.sink == "sys.stdout"
    assert file_sink is None or (
        isinstance(file_sink.sink, str) and file_sink.sink.endswith(".log")
    )
