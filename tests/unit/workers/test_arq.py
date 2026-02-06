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
    llm_provider: str = "ollama",
    fallback_enabled: bool = False,
    fallback_secondary_provider: str = "groq",
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
    mock_settings.llm.provider = llm_provider
    mock_settings.llm.groq.model = "llama3-70b-8192"
    mock_settings.llm.groq.timeout = 30
    mock_settings.llm.groq.max_retries = 3
    mock_settings.llm.groq.requests_per_minute = 30
    mock_settings.llm.ollama.url = "http://localhost:11434"
    mock_settings.llm.ollama.model = "llama2"
    mock_settings.llm.ollama.timeout = 60
    mock_settings.llm.ollama.max_retries = 2
    mock_settings.llm.fallback.enabled = fallback_enabled
    mock_settings.llm.fallback.secondary_provider = fallback_secondary_provider
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

    @pytest.mark.asyncio
    async def test_llm_client_none_when_groq_without_api_key(self) -> None:
        """Should set llm_client to None when Groq selected but API key not set."""
        ctx: dict[str, MagicMock] = {}
        mock_settings = _create_mock_settings(
            llm_enabled=True,
            llm_provider="groq",
            groq_api_key=None,
        )
        mock_redis = AsyncMock()

        with (
            patch("app.workers.arq.get_settings", return_value=mock_settings),
            patch("app.workers.arq.setup_logging"),
            patch("app.workers.arq.Redis.from_url", return_value=mock_redis),
        ):
            await startup(ctx)

            assert ctx["llm_client"] is None

    @pytest.mark.asyncio
    async def test_initializes_groq_primary_client(self) -> None:
        """Should initialize Groq as primary client when provider is groq."""
        ctx: dict[str, MagicMock] = {}
        mock_settings = _create_mock_settings(
            llm_enabled=True,
            llm_provider="groq",
            groq_api_key="test-groq-key",
        )
        mock_redis = AsyncMock()
        mock_groq_client = AsyncMock()
        mock_fallback_client = MagicMock()

        with (
            patch("app.workers.arq.get_settings", return_value=mock_settings),
            patch("app.workers.arq.setup_logging"),
            patch("app.workers.arq.Redis.from_url", return_value=mock_redis),
            patch("app.workers.arq.GroqClient", return_value=mock_groq_client),
            patch(
                "app.workers.arq.FallbackLLMClient", return_value=mock_fallback_client
            ),
        ):
            await startup(ctx)

            mock_groq_client.initialize.assert_called_once()
            assert ctx["llm_client"] is mock_fallback_client

    @pytest.mark.asyncio
    async def test_initializes_ollama_primary_client(self) -> None:
        """Should initialize Ollama as primary client when provider is ollama."""
        ctx: dict[str, MagicMock] = {}
        mock_settings = _create_mock_settings(
            llm_enabled=True,
            llm_provider="ollama",
        )
        mock_redis = AsyncMock()
        mock_ollama_client = AsyncMock()
        mock_fallback_client = MagicMock()

        with (
            patch("app.workers.arq.get_settings", return_value=mock_settings),
            patch("app.workers.arq.setup_logging"),
            patch("app.workers.arq.Redis.from_url", return_value=mock_redis),
            patch("app.workers.arq.OllamaClient", return_value=mock_ollama_client),
            patch(
                "app.workers.arq.FallbackLLMClient", return_value=mock_fallback_client
            ),
        ):
            await startup(ctx)

            mock_ollama_client.initialize.assert_called_once()
            assert ctx["llm_client"] is mock_fallback_client

    @pytest.mark.asyncio
    async def test_initializes_groq_fallback_when_enabled(self) -> None:
        """Should initialize Groq fallback when enabled with Ollama primary."""
        ctx: dict[str, MagicMock] = {}
        mock_settings = _create_mock_settings(
            llm_enabled=True,
            llm_provider="ollama",
            groq_api_key="test-groq-key",
            fallback_enabled=True,
            fallback_secondary_provider="groq",
        )
        mock_redis = AsyncMock()
        mock_ollama_client = AsyncMock()
        mock_groq_client = AsyncMock()
        mock_fallback_client = MagicMock()

        with (
            patch("app.workers.arq.get_settings", return_value=mock_settings),
            patch("app.workers.arq.setup_logging"),
            patch("app.workers.arq.Redis.from_url", return_value=mock_redis),
            patch("app.workers.arq.OllamaClient", return_value=mock_ollama_client),
            patch("app.workers.arq.GroqClient", return_value=mock_groq_client),
            patch(
                "app.workers.arq.FallbackLLMClient", return_value=mock_fallback_client
            ) as mock_fallback_class,
        ):
            await startup(ctx)

            # Both clients should be initialized
            mock_ollama_client.initialize.assert_called_once()
            mock_groq_client.initialize.assert_called_once()

            # FallbackLLMClient should be created with both clients
            mock_fallback_class.assert_called_once_with(
                primary=mock_ollama_client,
                secondary=mock_groq_client,
                fallback_enabled=True,
            )

    @pytest.mark.asyncio
    async def test_no_fallback_when_same_provider(self) -> None:
        """Should not create fallback when primary and secondary are same provider."""
        ctx: dict[str, MagicMock] = {}
        mock_settings = _create_mock_settings(
            llm_enabled=True,
            llm_provider="groq",
            groq_api_key="test-groq-key",
            fallback_enabled=True,
            fallback_secondary_provider="groq",
        )
        mock_redis = AsyncMock()
        mock_groq_client = AsyncMock()
        mock_fallback_client = MagicMock()

        with (
            patch("app.workers.arq.get_settings", return_value=mock_settings),
            patch("app.workers.arq.setup_logging"),
            patch("app.workers.arq.Redis.from_url", return_value=mock_redis),
            patch("app.workers.arq.GroqClient", return_value=mock_groq_client),
            patch(
                "app.workers.arq.FallbackLLMClient", return_value=mock_fallback_client
            ) as mock_fallback_class,
        ):
            await startup(ctx)

            # FallbackLLMClient should be created with secondary=None
            mock_fallback_class.assert_called_once_with(
                primary=mock_groq_client,
                secondary=None,
                fallback_enabled=True,
            )


class TestShutdown:
    """Tests for shutdown handler."""

    @pytest.mark.asyncio
    async def test_logs_shutdown(self) -> None:
        """Should log shutdown message."""
        ctx: dict[str, MagicMock] = {}

        with patch("app.workers.arq.logger") as mock_logger:
            await shutdown(ctx)

            mock_logger.info.assert_called_once_with("ARQ worker shutting down")

    @pytest.mark.asyncio
    async def test_closes_cache_client_when_present(self) -> None:
        """Should close cache client if it exists in context."""
        mock_cache_client = AsyncMock()
        ctx: dict[str, AsyncMock] = {"cache_client": mock_cache_client}

        await shutdown(ctx)

        mock_cache_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_closes_llm_client_when_present(self) -> None:
        """Should close LLM client if it exists in context."""
        mock_llm_client = AsyncMock()
        ctx: dict[str, AsyncMock] = {"llm_client": mock_llm_client}

        await shutdown(ctx)

        mock_llm_client.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_closes_both_clients_when_present(self) -> None:
        """Should close both cache and LLM clients when present."""
        mock_cache_client = AsyncMock()
        mock_llm_client = AsyncMock()
        ctx: dict[str, AsyncMock] = {
            "cache_client": mock_cache_client,
            "llm_client": mock_llm_client,
        }

        await shutdown(ctx)

        mock_cache_client.close.assert_called_once()
        mock_llm_client.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_empty_context(self) -> None:
        """Should handle empty context without errors."""
        ctx: dict[str, MagicMock] = {}

        # Should not raise
        await shutdown(ctx)


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
