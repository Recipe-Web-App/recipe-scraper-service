"""Unit tests for application factory.

Tests cover:
- create_app function
- Middleware setup
- Router setup
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI

from app.core.config import Settings
from app.factory import _setup_middleware, _setup_routers, create_app


pytestmark = pytest.mark.unit


class TestCreateApp:
    """Tests for create_app function."""

    def test_creates_fastapi_instance(self) -> None:
        """Should create a FastAPI instance."""
        settings = Settings(APP_ENV="local")

        with (
            patch("app.factory.setup_tracing"),
            patch("app.factory.setup_metrics"),
            patch("app.factory.setup_exception_handlers"),
        ):
            app = create_app(settings)

        assert isinstance(app, FastAPI)
        assert app.title == settings.app.name
        assert app.version == settings.app.version

    def test_stores_settings_in_state(self) -> None:
        """Should store settings in app state."""
        settings = Settings(APP_ENV="local")

        with (
            patch("app.factory.setup_tracing"),
            patch("app.factory.setup_metrics"),
            patch("app.factory.setup_exception_handlers"),
        ):
            app = create_app(settings)

        assert app.state.settings is settings

    def test_disables_docs_in_production(self) -> None:
        """Should disable docs endpoints in production."""
        settings = Settings(APP_ENV="production")

        with (
            patch("app.factory.setup_tracing"),
            patch("app.factory.setup_metrics"),
            patch("app.factory.setup_exception_handlers"),
        ):
            app = create_app(settings)

        assert app.docs_url is None
        assert app.redoc_url is None
        assert app.openapi_url is None

    def test_disables_docs_in_staging(self) -> None:
        """Should disable docs endpoints in staging."""
        settings = Settings(APP_ENV="staging")

        with (
            patch("app.factory.setup_tracing"),
            patch("app.factory.setup_metrics"),
            patch("app.factory.setup_exception_handlers"),
        ):
            app = create_app(settings)

        assert app.docs_url is None
        assert app.redoc_url is None
        assert app.openapi_url is None

    def test_enables_docs_in_local(self) -> None:
        """Should enable docs endpoints in local environment."""
        settings = Settings(APP_ENV="local")

        with (
            patch("app.factory.setup_tracing"),
            patch("app.factory.setup_metrics"),
            patch("app.factory.setup_exception_handlers"),
        ):
            app = create_app(settings)

        prefix = settings.api.v1_prefix
        assert app.docs_url == f"{prefix}/docs"
        assert app.redoc_url == f"{prefix}/redoc"
        assert app.openapi_url == f"{prefix}/openapi.json"

    def test_enables_docs_in_test(self) -> None:
        """Should enable docs endpoints in test environment."""
        settings = Settings(APP_ENV="test")

        with (
            patch("app.factory.setup_tracing"),
            patch("app.factory.setup_metrics"),
            patch("app.factory.setup_exception_handlers"),
        ):
            app = create_app(settings)

        prefix = settings.api.v1_prefix
        assert app.docs_url == f"{prefix}/docs"
        assert app.redoc_url == f"{prefix}/redoc"
        assert app.openapi_url == f"{prefix}/openapi.json"

    def test_enables_docs_in_development(self) -> None:
        """Should enable docs endpoints in development environment."""
        settings = Settings(APP_ENV="development")

        with (
            patch("app.factory.setup_tracing"),
            patch("app.factory.setup_metrics"),
            patch("app.factory.setup_exception_handlers"),
        ):
            app = create_app(settings)

        prefix = settings.api.v1_prefix
        assert app.docs_url == f"{prefix}/docs"
        assert app.redoc_url == f"{prefix}/redoc"
        assert app.openapi_url == f"{prefix}/openapi.json"

    def test_uses_default_settings_when_none_provided(self) -> None:
        """Should use get_settings when no settings provided."""
        settings = Settings(APP_ENV="local")

        with (
            patch("app.factory.get_settings", return_value=settings),
            patch("app.factory.setup_tracing"),
            patch("app.factory.setup_metrics"),
            patch("app.factory.setup_exception_handlers"),
        ):
            app = create_app()

        assert app.title == settings.app.name


class TestSetupMiddleware:
    """Tests for _setup_middleware function."""

    def test_adds_middleware_without_cors(self) -> None:
        """Should add middleware without CORS when origins empty."""
        app = FastAPI()
        mock_settings = MagicMock()
        mock_settings.api.cors_origins = []

        _setup_middleware(app, mock_settings)

        # Should have added 5 middleware (no CORS)
        # GZip, Logging, Timing, RequestID, SecurityHeaders
        assert len(app.user_middleware) == 5

    def test_adds_cors_middleware_when_origins_set(self) -> None:
        """Should add CORS middleware when origins configured."""
        app = FastAPI()
        mock_settings = MagicMock()
        mock_settings.api.cors_origins = ["http://localhost:3000"]

        _setup_middleware(app, mock_settings)

        # Should have added 6 middleware (including CORS)
        assert len(app.user_middleware) == 6


class TestSetupRouters:
    """Tests for _setup_routers function."""

    def test_mounts_v1_router(self) -> None:
        """Should mount v1 API router with prefix."""
        app = FastAPI()
        mock_settings = MagicMock()
        mock_settings.app.name = "test-app"
        mock_settings.app.version = "1.0.0"
        mock_settings.is_development = True
        mock_settings.api.v1_prefix = "/api/v1/recipe-scraper"

        _setup_routers(app, mock_settings)

        # Check that routes were added with prefix
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/v1/recipe-scraper/" in routes  # Root endpoint with prefix

    def test_creates_root_endpoint(self) -> None:
        """Should create root endpoint with prefix."""
        app = FastAPI()
        mock_settings = MagicMock()
        mock_settings.app.name = "test-app"
        mock_settings.app.version = "1.0.0"
        mock_settings.is_development = True
        mock_settings.api.v1_prefix = "/api/v1/recipe-scraper"

        _setup_routers(app, mock_settings)

        # Root should be in routes with prefix
        route_paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/v1/recipe-scraper/" in route_paths
