"""Unit tests for lifespan events.

Tests cover:
- Startup sequence
- Shutdown sequence
- Error handling during initialization
- LLM client initialization and shutdown
- Auth provider initialization in different modes
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import AuthMode
from app.core.events.lifespan import (
    _init_llm_client,
    _LLMClientHolder,
    _shutdown_llm_client,
    get_llm_client,
    lifespan,
)


pytestmark = pytest.mark.unit


def _create_mock_settings(
    *,
    auth_mode: str = "disabled",
    llm_enabled: bool = False,
    llm_provider: str = "ollama",
    fallback_enabled: bool = False,
    groq_api_key: str | None = None,
) -> MagicMock:
    """Create mock settings with nested structure for tests."""
    mock_settings = MagicMock()
    mock_settings.app.name = "test-app"
    mock_settings.app.debug = False
    mock_settings.APP_ENV = "test"
    mock_settings.logging.level = "INFO"
    mock_settings.logging.format = "json"
    mock_settings.is_development = False
    mock_settings.auth.mode = auth_mode

    # Auth mode enum
    if auth_mode == "introspection":
        mock_settings.auth_mode_enum = AuthMode.INTROSPECTION
    else:
        mock_settings.auth_mode_enum = AuthMode.DISABLED

    # LLM settings
    mock_settings.llm.enabled = llm_enabled
    mock_settings.llm.provider = llm_provider
    mock_settings.llm.cache.enabled = True
    mock_settings.llm.cache.ttl = 3600
    mock_settings.llm.ollama.url = "http://localhost:11434"
    mock_settings.llm.ollama.model = "mistral:7b"
    mock_settings.llm.ollama.timeout = 30.0
    mock_settings.llm.ollama.max_retries = 3
    mock_settings.llm.fallback.enabled = fallback_enabled
    mock_settings.llm.fallback.secondary_provider = "groq"
    mock_settings.llm.groq.url = "https://api.groq.com/openai/v1"
    mock_settings.llm.groq.model = "llama3-8b-8192"
    mock_settings.llm.groq.timeout = 30.0
    mock_settings.llm.groq.max_retries = 3
    mock_settings.llm.groq.requests_per_minute = 30.0
    mock_settings.GROQ_API_KEY = groq_api_key

    return mock_settings


class TestLifespan:
    """Tests for lifespan context manager."""

    @pytest.mark.asyncio
    async def test_startup_initializes_logging(self) -> None:
        """Should initialize logging on startup."""
        mock_app = MagicMock()
        mock_settings = _create_mock_settings()

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging") as mock_setup,
            patch("app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock),
            patch("app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock),
            patch(
                "app.core.events.lifespan.initialize_auth_provider",
                new_callable=AsyncMock,
            ),
            patch(
                "app.core.events.lifespan.shutdown_auth_provider",
                new_callable=AsyncMock,
            ),
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
        mock_settings = _create_mock_settings()

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging"),
            patch(
                "app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock
            ) as mock_redis,
            patch("app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock),
            patch(
                "app.core.events.lifespan.initialize_auth_provider",
                new_callable=AsyncMock,
            ),
            patch(
                "app.core.events.lifespan.shutdown_auth_provider",
                new_callable=AsyncMock,
            ),
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
        mock_settings = _create_mock_settings()

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging"),
            patch("app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock),
            patch(
                "app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock
            ) as mock_arq,
            patch(
                "app.core.events.lifespan.initialize_auth_provider",
                new_callable=AsyncMock,
            ),
            patch(
                "app.core.events.lifespan.shutdown_auth_provider",
                new_callable=AsyncMock,
            ),
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
        mock_settings = _create_mock_settings()

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging"),
            patch(
                "app.core.events.lifespan.init_redis_pools",
                new_callable=AsyncMock,
                side_effect=Exception("Redis connection failed"),
            ),
            patch("app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock),
            patch(
                "app.core.events.lifespan.initialize_auth_provider",
                new_callable=AsyncMock,
            ),
            patch(
                "app.core.events.lifespan.shutdown_auth_provider",
                new_callable=AsyncMock,
            ),
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
        mock_settings = _create_mock_settings()

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging"),
            patch("app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock),
            patch(
                "app.core.events.lifespan.get_arq_pool",
                new_callable=AsyncMock,
                side_effect=Exception("ARQ connection failed"),
            ),
            patch(
                "app.core.events.lifespan.initialize_auth_provider",
                new_callable=AsyncMock,
            ),
            patch(
                "app.core.events.lifespan.shutdown_auth_provider",
                new_callable=AsyncMock,
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
        mock_settings = _create_mock_settings()

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging"),
            patch("app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock),
            patch("app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock),
            patch(
                "app.core.events.lifespan.initialize_auth_provider",
                new_callable=AsyncMock,
            ),
            patch(
                "app.core.events.lifespan.shutdown_auth_provider",
                new_callable=AsyncMock,
            ),
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
        mock_settings = _create_mock_settings()

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging"),
            patch("app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock),
            patch("app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock),
            patch(
                "app.core.events.lifespan.initialize_auth_provider",
                new_callable=AsyncMock,
            ),
            patch(
                "app.core.events.lifespan.shutdown_auth_provider",
                new_callable=AsyncMock,
            ),
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
        mock_settings = _create_mock_settings()

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging"),
            patch("app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock),
            patch("app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock),
            patch(
                "app.core.events.lifespan.initialize_auth_provider",
                new_callable=AsyncMock,
            ),
            patch(
                "app.core.events.lifespan.shutdown_auth_provider",
                new_callable=AsyncMock,
            ),
            patch("app.core.events.lifespan.shutdown_tracing"),
            patch("app.core.events.lifespan.close_arq_pool", new_callable=AsyncMock),
            patch(
                "app.core.events.lifespan.close_redis_pools", new_callable=AsyncMock
            ) as mock_close_redis,
        ):
            async with lifespan(mock_app):
                pass

            mock_close_redis.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_auth_failure_raises(self) -> None:
        """Should raise when auth provider initialization fails."""
        mock_app = MagicMock()
        mock_settings = _create_mock_settings()

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging"),
            patch("app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock),
            patch("app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock),
            patch(
                "app.core.events.lifespan.initialize_auth_provider",
                new_callable=AsyncMock,
                side_effect=Exception("Auth provider failed"),
            ),
            patch(
                "app.core.events.lifespan.shutdown_auth_provider",
                new_callable=AsyncMock,
            ),
            patch("app.core.events.lifespan.shutdown_tracing"),
            patch("app.core.events.lifespan.close_arq_pool", new_callable=AsyncMock),
            patch("app.core.events.lifespan.close_redis_pools", new_callable=AsyncMock),
            pytest.raises(Exception, match="Auth provider failed"),
        ):
            async with lifespan(mock_app):
                pass

    @pytest.mark.asyncio
    async def test_startup_introspection_mode_gets_cache_client(self) -> None:
        """Should get cache client for auth when in introspection mode."""
        mock_app = MagicMock()
        mock_settings = _create_mock_settings(auth_mode="introspection")
        mock_cache_client = MagicMock()

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging"),
            patch("app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock),
            patch("app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock),
            patch(
                "app.core.events.lifespan.get_cache_client",
                new_callable=AsyncMock,
                return_value=mock_cache_client,
            ) as mock_get_cache,
            patch(
                "app.core.events.lifespan.initialize_auth_provider",
                new_callable=AsyncMock,
            ) as mock_init_auth,
            patch(
                "app.core.events.lifespan.shutdown_auth_provider",
                new_callable=AsyncMock,
            ),
            patch("app.core.events.lifespan.shutdown_tracing"),
            patch("app.core.events.lifespan.close_arq_pool", new_callable=AsyncMock),
            patch("app.core.events.lifespan.close_redis_pools", new_callable=AsyncMock),
        ):
            async with lifespan(mock_app):
                pass

            mock_get_cache.assert_called_once()
            mock_init_auth.assert_called_once_with(cache_client=mock_cache_client)

    @pytest.mark.asyncio
    async def test_startup_introspection_mode_continues_without_cache(self) -> None:
        """Should continue without cache if Redis unavailable in introspection mode."""
        mock_app = MagicMock()
        mock_settings = _create_mock_settings(auth_mode="introspection")

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging"),
            patch("app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock),
            patch("app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock),
            patch(
                "app.core.events.lifespan.get_cache_client",
                new_callable=AsyncMock,
                side_effect=Exception("Redis unavailable"),
            ),
            patch(
                "app.core.events.lifespan.initialize_auth_provider",
                new_callable=AsyncMock,
            ) as mock_init_auth,
            patch(
                "app.core.events.lifespan.shutdown_auth_provider",
                new_callable=AsyncMock,
            ),
            patch("app.core.events.lifespan.shutdown_tracing"),
            patch("app.core.events.lifespan.close_arq_pool", new_callable=AsyncMock),
            patch("app.core.events.lifespan.close_redis_pools", new_callable=AsyncMock),
        ):
            # Should not raise
            async with lifespan(mock_app):
                pass

            # Auth should be initialized with None cache
            mock_init_auth.assert_called_once_with(cache_client=None)

    @pytest.mark.asyncio
    async def test_startup_with_llm_enabled(self) -> None:
        """Should initialize LLM client when enabled."""
        mock_app = MagicMock()
        mock_settings = _create_mock_settings(llm_enabled=True)

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging"),
            patch("app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock),
            patch("app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock),
            patch(
                "app.core.events.lifespan.initialize_auth_provider",
                new_callable=AsyncMock,
            ),
            patch(
                "app.core.events.lifespan.shutdown_auth_provider",
                new_callable=AsyncMock,
            ),
            patch(
                "app.core.events.lifespan._init_llm_client",
                new_callable=AsyncMock,
            ) as mock_init_llm,
            patch(
                "app.core.events.lifespan._shutdown_llm_client",
                new_callable=AsyncMock,
            ),
            patch("app.core.events.lifespan.shutdown_tracing"),
            patch("app.core.events.lifespan.close_arq_pool", new_callable=AsyncMock),
            patch("app.core.events.lifespan.close_redis_pools", new_callable=AsyncMock),
        ):
            async with lifespan(mock_app):
                pass

            mock_init_llm.assert_called_once_with(mock_settings)

    @pytest.mark.asyncio
    async def test_startup_llm_failure_continues(self) -> None:
        """Should continue startup even if LLM initialization fails."""
        mock_app = MagicMock()
        mock_settings = _create_mock_settings(llm_enabled=True)

        with (
            patch("app.core.events.lifespan.get_settings", return_value=mock_settings),
            patch("app.core.events.lifespan.setup_logging"),
            patch("app.core.events.lifespan.init_redis_pools", new_callable=AsyncMock),
            patch("app.core.events.lifespan.get_arq_pool", new_callable=AsyncMock),
            patch(
                "app.core.events.lifespan.initialize_auth_provider",
                new_callable=AsyncMock,
            ),
            patch(
                "app.core.events.lifespan.shutdown_auth_provider",
                new_callable=AsyncMock,
            ),
            patch(
                "app.core.events.lifespan._init_llm_client",
                new_callable=AsyncMock,
                side_effect=Exception("LLM init failed"),
            ),
            patch(
                "app.core.events.lifespan._shutdown_llm_client",
                new_callable=AsyncMock,
            ),
            patch("app.core.events.lifespan.shutdown_tracing"),
            patch("app.core.events.lifespan.close_arq_pool", new_callable=AsyncMock),
            patch("app.core.events.lifespan.close_redis_pools", new_callable=AsyncMock),
        ):
            # Should not raise
            async with lifespan(mock_app):
                pass


# =============================================================================
# LLM Client Initialization Tests
# =============================================================================


class TestLLMClientInitialization:
    """Tests for _init_llm_client function."""

    @pytest.fixture(autouse=True)
    def reset_llm_holder(self) -> None:
        """Reset LLM client holder before each test."""
        _LLMClientHolder.client = None
        yield
        _LLMClientHolder.client = None

    @pytest.mark.asyncio
    async def test_init_llm_client_creates_primary(self) -> None:
        """Should create primary Ollama client."""
        mock_settings = _create_mock_settings(llm_enabled=True)

        with (
            patch(
                "app.core.events.lifespan.get_cache_client",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ),
            patch("app.core.events.lifespan.OllamaClient") as mock_ollama,
            patch("app.core.events.lifespan.FallbackLLMClient") as mock_fallback,
        ):
            mock_client = MagicMock()
            mock_client.initialize = AsyncMock()
            mock_fallback.return_value = mock_client

            await _init_llm_client(mock_settings)

            mock_ollama.assert_called_once()
            mock_fallback.assert_called_once()
            assert _LLMClientHolder.client is mock_client

    @pytest.mark.asyncio
    async def test_init_llm_client_with_groq_fallback(self) -> None:
        """Should create Groq client when fallback enabled with API key."""
        mock_settings = _create_mock_settings(
            llm_enabled=True,
            fallback_enabled=True,
            groq_api_key="test-api-key",
        )

        with (
            patch(
                "app.core.events.lifespan.get_cache_client",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ),
            patch("app.core.events.lifespan.OllamaClient"),
            patch("app.core.events.lifespan.GroqClient") as mock_groq,
            patch("app.core.events.lifespan.FallbackLLMClient") as mock_fallback,
        ):
            mock_client = MagicMock()
            mock_client.initialize = AsyncMock()
            mock_fallback.return_value = mock_client

            await _init_llm_client(mock_settings)

            mock_groq.assert_called_once()
            # Verify secondary was passed to FallbackLLMClient
            call_kwargs = mock_fallback.call_args[1]
            assert call_kwargs["secondary"] is not None

    @pytest.mark.asyncio
    async def test_init_llm_client_fallback_enabled_no_api_key(self) -> None:
        """Should warn when fallback enabled but no API key."""
        mock_settings = _create_mock_settings(
            llm_enabled=True,
            fallback_enabled=True,
            groq_api_key=None,
        )

        with (
            patch(
                "app.core.events.lifespan.get_cache_client",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ),
            patch("app.core.events.lifespan.OllamaClient"),
            patch("app.core.events.lifespan.GroqClient") as mock_groq,
            patch("app.core.events.lifespan.FallbackLLMClient") as mock_fallback,
            patch("app.core.events.lifespan.logger") as mock_logger,
        ):
            mock_client = MagicMock()
            mock_client.initialize = AsyncMock()
            mock_fallback.return_value = mock_client

            await _init_llm_client(mock_settings)

            # Groq should not be created
            mock_groq.assert_not_called()
            # Warning should be logged
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_init_llm_client_cache_unavailable(self) -> None:
        """Should continue without cache if Redis unavailable."""
        mock_settings = _create_mock_settings(llm_enabled=True)

        with (
            patch(
                "app.core.events.lifespan.get_cache_client",
                new_callable=AsyncMock,
                side_effect=Exception("Redis unavailable"),
            ),
            patch("app.core.events.lifespan.OllamaClient") as mock_ollama,
            patch("app.core.events.lifespan.FallbackLLMClient") as mock_fallback,
        ):
            mock_client = MagicMock()
            mock_client.initialize = AsyncMock()
            mock_fallback.return_value = mock_client

            await _init_llm_client(mock_settings)

            # Should still create client with cache_client=None
            call_kwargs = mock_ollama.call_args[1]
            assert call_kwargs["cache_client"] is None

    @pytest.mark.asyncio
    async def test_init_llm_client_groq_as_primary(self) -> None:
        """Should create GroqClient as primary when provider is groq."""
        mock_settings = _create_mock_settings(
            llm_enabled=True,
            llm_provider="groq",
            groq_api_key="test-api-key",
        )

        with (
            patch(
                "app.core.events.lifespan.get_cache_client",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ),
            patch("app.core.events.lifespan.OllamaClient") as mock_ollama,
            patch("app.core.events.lifespan.GroqClient") as mock_groq,
            patch("app.core.events.lifespan.FallbackLLMClient") as mock_fallback,
        ):
            mock_client = MagicMock()
            mock_client.initialize = AsyncMock()
            mock_fallback.return_value = mock_client

            await _init_llm_client(mock_settings)

            # GroqClient should be created as primary
            mock_groq.assert_called_once()
            # OllamaClient should NOT be created
            mock_ollama.assert_not_called()
            # Verify GroqClient was passed as primary to FallbackLLMClient
            call_kwargs = mock_fallback.call_args[1]
            assert call_kwargs["primary"] is mock_groq.return_value

    @pytest.mark.asyncio
    async def test_init_llm_client_groq_primary_no_api_key(self) -> None:
        """Should warn and return early when groq is primary but no API key."""
        mock_settings = _create_mock_settings(
            llm_enabled=True,
            llm_provider="groq",
            groq_api_key=None,
        )

        with (
            patch(
                "app.core.events.lifespan.get_cache_client",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ),
            patch("app.core.events.lifespan.OllamaClient") as mock_ollama,
            patch("app.core.events.lifespan.GroqClient") as mock_groq,
            patch("app.core.events.lifespan.FallbackLLMClient") as mock_fallback,
            patch("app.core.events.lifespan.logger") as mock_logger,
        ):
            await _init_llm_client(mock_settings)

            # Should warn about missing API key
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "GROQ_API_KEY" in warning_call
            # Neither client should be created
            mock_groq.assert_not_called()
            mock_ollama.assert_not_called()
            mock_fallback.assert_not_called()
            # LLM client should not be set
            assert _LLMClientHolder.client is None

    @pytest.mark.asyncio
    async def test_init_llm_client_ollama_as_primary_explicit(self) -> None:
        """Should create OllamaClient as primary when provider is ollama."""
        mock_settings = _create_mock_settings(
            llm_enabled=True,
            llm_provider="ollama",
        )

        with (
            patch(
                "app.core.events.lifespan.get_cache_client",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ),
            patch("app.core.events.lifespan.OllamaClient") as mock_ollama,
            patch("app.core.events.lifespan.GroqClient") as mock_groq,
            patch("app.core.events.lifespan.FallbackLLMClient") as mock_fallback,
        ):
            mock_client = MagicMock()
            mock_client.initialize = AsyncMock()
            mock_fallback.return_value = mock_client

            await _init_llm_client(mock_settings)

            # OllamaClient should be created as primary
            mock_ollama.assert_called_once()
            # GroqClient should NOT be created (no fallback)
            mock_groq.assert_not_called()
            # Verify OllamaClient was passed as primary
            call_kwargs = mock_fallback.call_args[1]
            assert call_kwargs["primary"] is mock_ollama.return_value


# =============================================================================
# LLM Client Shutdown Tests
# =============================================================================


class TestLLMClientShutdown:
    """Tests for _shutdown_llm_client function."""

    @pytest.fixture(autouse=True)
    def reset_llm_holder(self) -> None:
        """Reset LLM client holder before each test."""
        _LLMClientHolder.client = None
        yield
        _LLMClientHolder.client = None

    @pytest.mark.asyncio
    async def test_shutdown_llm_client_when_initialized(self) -> None:
        """Should shutdown client when it exists."""
        mock_client = MagicMock()
        mock_client.shutdown = AsyncMock()
        _LLMClientHolder.client = mock_client

        await _shutdown_llm_client()

        mock_client.shutdown.assert_called_once()
        assert _LLMClientHolder.client is None

    @pytest.mark.asyncio
    async def test_shutdown_llm_client_when_not_initialized(self) -> None:
        """Should handle shutdown when client is None."""
        _LLMClientHolder.client = None

        # Should not raise
        await _shutdown_llm_client()

        assert _LLMClientHolder.client is None


# =============================================================================
# get_llm_client Tests
# =============================================================================


class TestGetLLMClient:
    """Tests for get_llm_client function."""

    @pytest.fixture(autouse=True)
    def reset_llm_holder(self) -> None:
        """Reset LLM client holder before each test."""
        _LLMClientHolder.client = None
        yield
        _LLMClientHolder.client = None

    def test_get_llm_client_returns_client(self) -> None:
        """Should return client when initialized."""
        mock_client = MagicMock()
        _LLMClientHolder.client = mock_client

        result = get_llm_client()

        assert result is mock_client

    def test_get_llm_client_raises_when_not_initialized(self) -> None:
        """Should raise RuntimeError when client not initialized."""
        _LLMClientHolder.client = None

        with pytest.raises(RuntimeError, match="LLM client not initialized"):
            get_llm_client()
