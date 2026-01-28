"""Unit tests for database connection module.

Tests cover:
- Connection pool initialization
- Connection pool closing
- Pool getter
- Health checks
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.database.connection as db_module
from app.database.connection import (
    check_database_health,
    close_database_pool,
    get_database_pool,
    init_database_pool,
)


if TYPE_CHECKING:
    from collections.abc import Generator

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def reset_database_globals() -> Generator[None]:
    """Reset database global state before and after each test."""
    db_module._pool = None
    yield
    db_module._pool = None


class TestGetDatabasePool:
    """Tests for get_database_pool function."""

    def test_raises_when_not_initialized(self) -> None:
        """Should raise RuntimeError when pool not initialized."""
        with pytest.raises(RuntimeError, match="not initialized"):
            get_database_pool()

    def test_returns_pool_when_initialized(self) -> None:
        """Should return pool when initialized."""
        mock_pool = MagicMock()
        db_module._pool = mock_pool

        result = get_database_pool()

        assert result is mock_pool


class TestInitDatabasePool:
    """Tests for init_database_pool function."""

    @pytest.mark.asyncio
    async def test_initializes_pool(self) -> None:
        """Should initialize the database pool."""
        mock_settings = MagicMock()
        mock_settings.database.host = "localhost"
        mock_settings.database.port = 5432
        mock_settings.database.name = "test"
        mock_settings.database.user = "postgres"
        mock_settings.database.min_pool_size = 1
        mock_settings.database.max_pool_size = 5
        mock_settings.database.command_timeout = 30.0
        mock_settings.database.ssl = False
        mock_settings.DATABASE_PASSWORD = ""

        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_pool.acquire = MagicMock(return_value=AsyncMock())
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("app.database.connection.get_settings", return_value=mock_settings),
            patch(
                "app.database.connection.asyncpg.create_pool",
                new_callable=AsyncMock,
                return_value=mock_pool,
            ),
        ):
            await init_database_pool()

            assert db_module._pool is not None

    @pytest.mark.asyncio
    async def test_verifies_connection(self) -> None:
        """Should verify connection with SELECT 1."""
        mock_settings = MagicMock()
        mock_settings.database.host = "localhost"
        mock_settings.database.port = 5432
        mock_settings.database.name = "test"
        mock_settings.database.user = "postgres"
        mock_settings.database.min_pool_size = 1
        mock_settings.database.max_pool_size = 5
        mock_settings.database.command_timeout = 30.0
        mock_settings.database.ssl = False
        mock_settings.DATABASE_PASSWORD = ""

        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_pool.acquire = MagicMock(return_value=AsyncMock())
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("app.database.connection.get_settings", return_value=mock_settings),
            patch(
                "app.database.connection.asyncpg.create_pool",
                new_callable=AsyncMock,
                return_value=mock_pool,
            ),
        ):
            await init_database_pool()

            mock_conn.fetchval.assert_called_once_with("SELECT 1")


class TestCloseDatabasePool:
    """Tests for close_database_pool function."""

    @pytest.mark.asyncio
    async def test_closes_pool(self) -> None:
        """Should close the database pool."""
        mock_pool = AsyncMock()
        db_module._pool = mock_pool

        await close_database_pool()

        mock_pool.close.assert_called_once()
        assert db_module._pool is None

    @pytest.mark.asyncio
    async def test_handles_none_pool(self) -> None:
        """Should handle None pool gracefully."""
        await close_database_pool()  # Should not raise


class TestCheckDatabaseHealth:
    """Tests for check_database_health function."""

    @pytest.mark.asyncio
    async def test_returns_healthy_when_connected(self) -> None:
        """Should return healthy status when pool responds."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_pool.acquire = MagicMock(return_value=AsyncMock())
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        db_module._pool = mock_pool

        result = await check_database_health()

        assert result["database"] == "healthy"

    @pytest.mark.asyncio
    async def test_returns_not_initialized_when_no_pool(self) -> None:
        """Should return not_initialized when pool is None."""
        result = await check_database_health()

        assert result["database"] == "not_initialized"

    @pytest.mark.asyncio
    async def test_returns_unhealthy_on_error(self) -> None:
        """Should return unhealthy when query fails."""
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=AsyncMock())
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("Connection failed")
        )
        db_module._pool = mock_pool

        result = await check_database_health()

        assert result["database"] == "unhealthy"
