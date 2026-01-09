"""Unit tests for lifespan events.

Tests cover:
- Startup sequence
- Shutdown sequence
- Error handling during initialization
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.events.lifespan import lifespan


pytestmark = pytest.mark.unit


class TestLifespan:
    """Tests for lifespan context manager."""

    @pytest.mark.asyncio
    async def test_startup_initializes_logging(self) -> None:
        """Should initialize logging on startup."""
        mock_app = MagicMock()
        mock_settings = MagicMock()
        mock_settings.APP_NAME = "test-app"
        mock_settings.ENVIRONMENT = "test"
        mock_settings.DEBUG = False
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "json"
        mock_settings.is_development = False

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging") as mock_setup,
            patch("app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock),
            patch("app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock),
            patch("app.core.events.lifespan.shutdown_tracing"),
            patch("app.core.events.lifespan.close_arq_pool", new_callable=AsyncMock),
            patch("app.core.events.lifespan.close_redis_pools", new_callable=AsyncMock),
        ):
            async with lifespan(mock_app):
                pass

            mock_setup.assert_called_once_with(
                log_level="INFO",
                log_format="json",
                is_development=False,
            )

    @pytest.mark.asyncio
    async def test_startup_initializes_redis(self) -> None:
        """Should initialize Redis pools on startup."""
        mock_app = MagicMock()
        mock_settings = MagicMock()
        mock_settings.APP_NAME = "test-app"
        mock_settings.ENVIRONMENT = "test"
        mock_settings.DEBUG = False
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "json"
        mock_settings.is_development = False

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging"),
            patch(
                "app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock
            ) as mock_redis,
            patch("app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock),
            patch("app.core.events.lifespan.shutdown_tracing"),
            patch("app.core.events.lifespan.close_arq_pool", new_callable=AsyncMock),
            patch("app.core.events.lifespan.close_redis_pools", new_callable=AsyncMock),
        ):
            async with lifespan(mock_app):
                pass

            mock_redis.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_initializes_arq_pool(self) -> None:
        """Should initialize ARQ pool on startup."""
        mock_app = MagicMock()
        mock_settings = MagicMock()
        mock_settings.APP_NAME = "test-app"
        mock_settings.ENVIRONMENT = "test"
        mock_settings.DEBUG = False
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "json"
        mock_settings.is_development = False

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging"),
            patch("app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock),
            patch(
                "app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock
            ) as mock_arq,
            patch("app.core.events.lifespan.shutdown_tracing"),
            patch("app.core.events.lifespan.close_arq_pool", new_callable=AsyncMock),
            patch("app.core.events.lifespan.close_redis_pools", new_callable=AsyncMock),
        ):
            async with lifespan(mock_app):
                pass

            mock_arq.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_continues_on_redis_failure(self) -> None:
        """Should continue startup even if Redis initialization fails."""
        mock_app = MagicMock()
        mock_settings = MagicMock()
        mock_settings.APP_NAME = "test-app"
        mock_settings.ENVIRONMENT = "test"
        mock_settings.DEBUG = False
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "json"
        mock_settings.is_development = False

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging"),
            patch(
                "app.core.events.lifespan.init_redis_pools",
                new_callable=AsyncMock,
                side_effect=Exception("Redis connection failed"),
            ),
            patch("app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock),
            patch("app.core.events.lifespan.shutdown_tracing"),
            patch("app.core.events.lifespan.close_arq_pool", new_callable=AsyncMock),
            patch("app.core.events.lifespan.close_redis_pools", new_callable=AsyncMock),
        ):
            # Should not raise
            async with lifespan(mock_app):
                pass

    @pytest.mark.asyncio
    async def test_startup_continues_on_arq_failure(self) -> None:
        """Should continue startup even if ARQ initialization fails."""
        mock_app = MagicMock()
        mock_settings = MagicMock()
        mock_settings.APP_NAME = "test-app"
        mock_settings.ENVIRONMENT = "test"
        mock_settings.DEBUG = False
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "json"
        mock_settings.is_development = False

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging"),
            patch("app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock),
            patch(
                "app.core.events.lifespan.get_arq_pool",
                new_callable=AsyncMock,
                side_effect=Exception("ARQ connection failed"),
            ),
            patch("app.core.events.lifespan.shutdown_tracing"),
            patch("app.core.events.lifespan.close_arq_pool", new_callable=AsyncMock),
            patch("app.core.events.lifespan.close_redis_pools", new_callable=AsyncMock),
        ):
            # Should not raise
            async with lifespan(mock_app):
                pass

    @pytest.mark.asyncio
    async def test_shutdown_closes_tracing(self) -> None:
        """Should shutdown tracing on application shutdown."""
        mock_app = MagicMock()
        mock_settings = MagicMock()
        mock_settings.APP_NAME = "test-app"
        mock_settings.ENVIRONMENT = "test"
        mock_settings.DEBUG = False
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "json"
        mock_settings.is_development = False

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging"),
            patch("app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock),
            patch("app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock),
            patch("app.core.events.lifespan.shutdown_tracing") as mock_shutdown_tracing,
            patch("app.core.events.lifespan.close_arq_pool", new_callable=AsyncMock),
            patch("app.core.events.lifespan.close_redis_pools", new_callable=AsyncMock),
        ):
            async with lifespan(mock_app):
                pass

            mock_shutdown_tracing.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_closes_arq_pool(self) -> None:
        """Should close ARQ pool on shutdown."""
        mock_app = MagicMock()
        mock_settings = MagicMock()
        mock_settings.APP_NAME = "test-app"
        mock_settings.ENVIRONMENT = "test"
        mock_settings.DEBUG = False
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "json"
        mock_settings.is_development = False

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging"),
            patch("app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock),
            patch("app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock),
            patch("app.core.events.lifespan.shutdown_tracing"),
            patch(
                "app.core.events.lifespan.close_arq_pool", new_callable=AsyncMock
            ) as mock_close_arq,
            patch("app.core.events.lifespan.close_redis_pools", new_callable=AsyncMock),
        ):
            async with lifespan(mock_app):
                pass

            mock_close_arq.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_closes_redis_pools(self) -> None:
        """Should close Redis pools on shutdown."""
        mock_app = MagicMock()
        mock_settings = MagicMock()
        mock_settings.APP_NAME = "test-app"
        mock_settings.ENVIRONMENT = "test"
        mock_settings.DEBUG = False
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "json"
        mock_settings.is_development = False

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging"),
            patch("app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock),
            patch("app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock),
            patch("app.core.events.lifespan.shutdown_tracing"),
            patch("app.core.events.lifespan.close_arq_pool", new_callable=AsyncMock),
            patch(
                "app.core.events.lifespan.close_redis_pools", new_callable=AsyncMock
            ) as mock_close_redis,
        ):
            async with lifespan(mock_app):
                pass

            mock_close_redis.assert_called_once()
