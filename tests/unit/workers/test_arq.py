"""Unit tests for ARQ worker configuration.

Tests cover:
- Worker settings
- Redis settings retrieval
- Startup/shutdown handlers
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers.arq import WorkerSettings, get_redis_settings, shutdown, startup


pytestmark = pytest.mark.unit


def _create_mock_settings(
    password: str | None = None,
    llm_enabled: bool = False,
    groq_api_key: str | None = None,
) -> MagicMock:
    """Create mock settings with nested structure."""
    mock_settings = MagicMock()
    mock_settings.redis.host = "localhost"
    mock_settings.redis.port = 6379
    mock_settings.redis.queue_db = 1
    mock_settings.REDIS_PASSWORD = password
    mock_settings.logging.level = "INFO"
    mock_settings.logging.format = "json"
    mock_settings.is_development = False
    mock_settings.APP_ENV = "test"
    mock_settings.redis_cache_url = "redis://localhost:6379/0"
    mock_settings.llm.enabled = llm_enabled
    mock_settings.GROQ_API_KEY = groq_api_key
    return mock_settings


class TestGetRedisSettings:
    """Tests for get_redis_settings function."""

    def test_returns_redis_settings(self) -> None:
        """Should return RedisSettings with correct values."""
        mock_settings = _create_mock_settings(password="secret")

        with patch("app.workers.arq.get_settings", return_value=mock_settings):
            result = get_redis_settings()

        assert result.host == "localhost"
        assert result.port == 6379
        assert result.password == "secret"
        assert result.database == 1

    def test_handles_no_password(self) -> None:
        """Should handle missing password."""
        mock_settings = _create_mock_settings(password=None)
        mock_settings.redis.queue_db = 0

        with patch("app.workers.arq.get_settings", return_value=mock_settings):
            result = get_redis_settings()

        assert result.password is None

    def test_handles_empty_password(self) -> None:
        """Should treat empty string as no password."""
        mock_settings = _create_mock_settings(password="")
        mock_settings.redis.queue_db = 0

        with patch("app.workers.arq.get_settings", return_value=mock_settings):
            result = get_redis_settings()

        assert result.password is None


class TestStartup:
    """Tests for startup handler."""

    @pytest.mark.asyncio
    async def test_sets_up_logging(self) -> None:
        """Should set up logging with correct settings."""
        ctx: dict[str, MagicMock] = {}
        mock_settings = _create_mock_settings()
        mock_settings.logging.level = "DEBUG"
        mock_redis = AsyncMock()

        with (
            patch("app.workers.arq.get_settings", return_value=mock_settings),
            patch("app.workers.arq.setup_logging") as mock_setup,
            patch("app.workers.arq.Redis.from_url", return_value=mock_redis),
        ):
            await startup(ctx)

            mock_setup.assert_called_once_with(
                log_level="DEBUG",
                log_format="json",
                is_development=False,
            )

    @pytest.mark.asyncio
    async def test_stores_settings_in_context(self) -> None:
        """Should store settings in worker context."""
        ctx: dict[str, MagicMock] = {}
        mock_settings = _create_mock_settings()
        mock_redis = AsyncMock()

        with (
            patch("app.workers.arq.get_settings", return_value=mock_settings),
            patch("app.workers.arq.setup_logging"),
            patch("app.workers.arq.Redis.from_url", return_value=mock_redis),
        ):
            await startup(ctx)

            assert ctx["settings"] is mock_settings

    @pytest.mark.asyncio
    async def test_initializes_cache_client(self) -> None:
        """Should initialize cache client in context."""
        ctx: dict[str, MagicMock] = {}
        mock_settings = _create_mock_settings()
        mock_redis = AsyncMock()

        with (
            patch("app.workers.arq.get_settings", return_value=mock_settings),
            patch("app.workers.arq.setup_logging"),
            patch("app.workers.arq.Redis.from_url", return_value=mock_redis),
        ):
            await startup(ctx)

            assert ctx["cache_client"] is mock_redis

    @pytest.mark.asyncio
    async def test_llm_client_none_when_disabled(self) -> None:
        """Should set llm_client to None when LLM is disabled."""
        ctx: dict[str, MagicMock] = {}
        mock_settings = _create_mock_settings(llm_enabled=False)
        mock_redis = AsyncMock()

        with (
            patch("app.workers.arq.get_settings", return_value=mock_settings),
            patch("app.workers.arq.setup_logging"),
            patch("app.workers.arq.Redis.from_url", return_value=mock_redis),
        ):
            await startup(ctx)

            assert ctx["llm_client"] is None


class TestShutdown:
    """Tests for shutdown handler."""

    @pytest.mark.asyncio
    async def test_logs_shutdown(self) -> None:
        """Should log shutdown message."""
        ctx: dict[str, MagicMock] = {}

        with patch("app.workers.arq.logger") as mock_logger:
            await shutdown(ctx)

            mock_logger.info.assert_called_once_with("ARQ worker shutting down")


class TestWorkerSettings:
    """Tests for WorkerSettings class."""

    def test_has_redis_settings(self) -> None:
        """Should have redis_settings attribute."""
        assert hasattr(WorkerSettings, "redis_settings")

    def test_has_lifecycle_hooks(self) -> None:
        """Should have startup and shutdown hooks."""
        assert WorkerSettings.on_startup is startup
        assert WorkerSettings.on_shutdown is shutdown

    def test_has_job_configuration(self) -> None:
        """Should have job configuration attributes."""
        assert WorkerSettings.job_timeout > 0
        assert WorkerSettings.max_jobs > 0
        assert WorkerSettings.keep_result > 0
        assert WorkerSettings.max_tries >= 1

    def test_has_registered_functions(self) -> None:
        """Should have registered task functions."""
        assert hasattr(WorkerSettings, "functions")
        assert len(WorkerSettings.functions) > 0

    def test_has_cron_jobs(self) -> None:
        """Should have cron jobs configured."""
        assert hasattr(WorkerSettings, "cron_jobs")
        assert isinstance(WorkerSettings.cron_jobs, list)
