"""Unit tests for Redis client module.

Tests cover:
- Connection pool initialization
- Connection pool closing
- Client getters
- Health checks
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as async_redis

import app.cache.redis as redis_module
from app.cache.redis import (
    check_redis_health,
    close_redis_pools,
    get_cache_client,
    get_queue_client,
    get_rate_limit_client,
    init_redis_pools,
)


if TYPE_CHECKING:
    from collections.abc import Generator

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def reset_redis_globals() -> Generator[None]:
    """Reset Redis global state before and after each test."""
    # Reset all global variables
    redis_module._cache_pool = None
    redis_module._queue_pool = None
    redis_module._rate_limit_pool = None
    redis_module._cache_client = None
    redis_module._queue_client = None
    redis_module._rate_limit_client = None
    yield
    # Cleanup
    redis_module._cache_pool = None
    redis_module._queue_pool = None
    redis_module._rate_limit_pool = None
    redis_module._cache_client = None
    redis_module._queue_client = None
    redis_module._rate_limit_client = None


class TestGetCacheClient:
    """Tests for get_cache_client function."""

    def test_raises_when_not_initialized(self) -> None:
        """Should raise RuntimeError when client not initialized."""
        with pytest.raises(RuntimeError, match="not initialized"):
            get_cache_client()

    def test_returns_client_when_initialized(self) -> None:
        """Should return client when initialized."""
        mock_client = MagicMock()
        redis_module._cache_client = mock_client

        result = get_cache_client()

        assert result is mock_client


class TestGetQueueClient:
    """Tests for get_queue_client function."""

    def test_raises_when_not_initialized(self) -> None:
        """Should raise RuntimeError when client not initialized."""
        with pytest.raises(RuntimeError, match="not initialized"):
            get_queue_client()

    def test_returns_client_when_initialized(self) -> None:
        """Should return client when initialized."""
        mock_client = MagicMock()
        redis_module._queue_client = mock_client

        result = get_queue_client()

        assert result is mock_client


class TestGetRateLimitClient:
    """Tests for get_rate_limit_client function."""

    def test_raises_when_not_initialized(self) -> None:
        """Should raise RuntimeError when client not initialized."""
        with pytest.raises(RuntimeError, match="not initialized"):
            get_rate_limit_client()

    def test_returns_client_when_initialized(self) -> None:
        """Should return client when initialized."""
        mock_client = MagicMock()
        redis_module._rate_limit_client = mock_client

        result = get_rate_limit_client()

        assert result is mock_client


class TestInitRedisPools:
    """Tests for init_redis_pools function."""

    @pytest.mark.asyncio
    async def test_initializes_all_pools(self) -> None:
        """Should initialize all Redis pools."""
        mock_settings = MagicMock()
        mock_settings.REDIS_HOST = "localhost"
        mock_settings.REDIS_PORT = 6379
        mock_settings.REDIS_CACHE_URL = "redis://localhost:6379/0"
        mock_settings.REDIS_QUEUE_URL = "redis://localhost:6379/1"
        mock_settings.REDIS_RATE_LIMIT_URL = "redis://localhost:6379/2"

        mock_pool = MagicMock()
        mock_client = AsyncMock()

        with (
            patch("app.cache.redis.get_settings", return_value=mock_settings),
            patch("app.cache.redis.ConnectionPool.from_url", return_value=mock_pool),
            patch("app.cache.redis.redis.Redis", return_value=mock_client),
        ):
            await init_redis_pools()

            # Verify clients were set
            assert redis_module._cache_client is not None
            assert redis_module._queue_client is not None
            assert redis_module._rate_limit_client is not None

    @pytest.mark.asyncio
    async def test_verifies_connections(self) -> None:
        """Should ping all connections to verify."""
        mock_settings = MagicMock()
        mock_settings.REDIS_HOST = "localhost"
        mock_settings.REDIS_PORT = 6379
        mock_settings.REDIS_CACHE_URL = "redis://localhost:6379/0"
        mock_settings.REDIS_QUEUE_URL = "redis://localhost:6379/1"
        mock_settings.REDIS_RATE_LIMIT_URL = "redis://localhost:6379/2"

        mock_pool = MagicMock()
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()

        with (
            patch("app.cache.redis.get_settings", return_value=mock_settings),
            patch("app.cache.redis.ConnectionPool.from_url", return_value=mock_pool),
            patch("app.cache.redis.redis.Redis", return_value=mock_client),
        ):
            await init_redis_pools()

            # Should have called ping on all clients (3 times)
            assert mock_client.ping.call_count == 3


class TestCloseRedisPools:
    """Tests for close_redis_pools function."""

    @pytest.mark.asyncio
    async def test_closes_all_clients(self) -> None:
        """Should close all Redis clients."""
        mock_cache_client = AsyncMock()
        mock_queue_client = AsyncMock()
        mock_rate_limit_client = AsyncMock()

        redis_module._cache_client = mock_cache_client
        redis_module._queue_client = mock_queue_client
        redis_module._rate_limit_client = mock_rate_limit_client

        await close_redis_pools()

        mock_cache_client.close.assert_called_once()
        mock_queue_client.close.assert_called_once()
        mock_rate_limit_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnects_all_pools(self) -> None:
        """Should disconnect all connection pools."""
        mock_cache_pool = AsyncMock()
        mock_queue_pool = AsyncMock()
        mock_rate_limit_pool = AsyncMock()

        redis_module._cache_pool = mock_cache_pool
        redis_module._queue_pool = mock_queue_pool
        redis_module._rate_limit_pool = mock_rate_limit_pool

        await close_redis_pools()

        mock_cache_pool.disconnect.assert_called_once()
        mock_queue_pool.disconnect.assert_called_once()
        mock_rate_limit_pool.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_none_clients(self) -> None:
        """Should handle None clients gracefully."""
        # All clients are None (default)
        await close_redis_pools()  # Should not raise

    @pytest.mark.asyncio
    async def test_resets_globals_to_none(self) -> None:
        """Should reset all globals to None."""
        redis_module._cache_client = MagicMock()
        redis_module._cache_client.close = AsyncMock()
        redis_module._cache_pool = MagicMock()
        redis_module._cache_pool.disconnect = AsyncMock()

        await close_redis_pools()

        assert redis_module._cache_client is None
        assert redis_module._cache_pool is None


class TestCheckRedisHealth:
    """Tests for check_redis_health function."""

    @pytest.mark.asyncio
    async def test_returns_healthy_when_all_connected(self) -> None:
        """Should return healthy status when all clients respond to ping."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()

        redis_module._cache_client = mock_client
        redis_module._queue_client = mock_client
        redis_module._rate_limit_client = mock_client

        result = await check_redis_health()

        assert result["redis_cache"] == "healthy"
        assert result["redis_queue"] == "healthy"
        assert result["redis_rate_limit"] == "healthy"

    @pytest.mark.asyncio
    async def test_returns_not_initialized_when_no_client(self) -> None:
        """Should return not_initialized when clients are None."""
        # Clients are None by default

        result = await check_redis_health()

        assert result["redis_cache"] == "not_initialized"
        assert result["redis_queue"] == "not_initialized"
        assert result["redis_rate_limit"] == "not_initialized"

    @pytest.mark.asyncio
    async def test_returns_unhealthy_on_connection_error(self) -> None:
        """Should return unhealthy on connection error."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(
            side_effect=async_redis.ConnectionError("Connection refused")
        )

        redis_module._cache_client = mock_client
        redis_module._queue_client = mock_client
        redis_module._rate_limit_client = mock_client

        result = await check_redis_health()

        assert result["redis_cache"] == "unhealthy"
        assert result["redis_queue"] == "unhealthy"
        assert result["redis_rate_limit"] == "unhealthy"
