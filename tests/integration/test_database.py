"""Integration tests for database module with testcontainers.

Tests cover:
- Connection pool initialization with real PostgreSQL
- Health check functionality
- Repository queries (when test data available)
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from testcontainers.postgres import PostgresContainer

import app.database.connection as db_module
from app.database.connection import (
    check_database_health,
    close_database_pool,
    init_database_pool,
)


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer]:
    """Start a PostgreSQL container for the test session."""
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def postgres_config(postgres_container: PostgresContainer) -> dict[str, str | int]:
    """Get PostgreSQL connection config from container."""
    return {
        "host": postgres_container.get_container_host_ip(),
        "port": int(postgres_container.get_exposed_port(5432)),
        "user": "test",
        "password": "test",
        "database": "test",
    }


@pytest.fixture(autouse=True)
async def reset_database_state() -> AsyncGenerator[None]:
    """Reset database module state before and after each test."""
    db_module._pool = None
    yield
    await close_database_pool()


class TestDatabaseConnectionIntegration:
    """Integration tests for database connection."""

    @pytest.mark.asyncio
    async def test_init_and_close_pool(
        self,
        postgres_config: dict[str, str | int],
    ) -> None:
        """Should initialize and close database pool successfully."""
        mock_settings = MagicMock()
        mock_settings.database.host = postgres_config["host"]
        mock_settings.database.port = postgres_config["port"]
        mock_settings.database.name = postgres_config["database"]
        mock_settings.database.user = postgres_config["user"]
        mock_settings.database.min_pool_size = 1
        mock_settings.database.max_pool_size = 5
        mock_settings.database.command_timeout = 30.0
        mock_settings.database.ssl = False
        mock_settings.DATABASE_PASSWORD = postgres_config["password"]

        with patch("app.database.connection.get_settings", return_value=mock_settings):
            # Initialize pool
            await init_database_pool()
            assert db_module._pool is not None

            # Close pool
            await close_database_pool()
            assert db_module._pool is None

    @pytest.mark.asyncio
    async def test_health_check_with_real_connection(
        self,
        postgres_config: dict[str, str | int],
    ) -> None:
        """Should return healthy status with real PostgreSQL."""
        mock_settings = MagicMock()
        mock_settings.database.host = postgres_config["host"]
        mock_settings.database.port = postgres_config["port"]
        mock_settings.database.name = postgres_config["database"]
        mock_settings.database.user = postgres_config["user"]
        mock_settings.database.min_pool_size = 1
        mock_settings.database.max_pool_size = 5
        mock_settings.database.command_timeout = 30.0
        mock_settings.database.ssl = False
        mock_settings.DATABASE_PASSWORD = postgres_config["password"]

        with patch("app.database.connection.get_settings", return_value=mock_settings):
            await init_database_pool()

            result = await check_database_health()

            assert result["database"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_returns_not_initialized(self) -> None:
        """Should return not_initialized when pool not created."""
        result = await check_database_health()

        assert result["database"] == "not_initialized"


class TestDatabaseConnectionFailures:
    """Tests for database connection failure scenarios."""

    @pytest.mark.asyncio
    async def test_init_fails_with_invalid_host(self) -> None:
        """Should raise when cannot connect to database."""
        mock_settings = MagicMock()
        mock_settings.database.host = "invalid-host-that-does-not-exist"
        mock_settings.database.port = 5432
        mock_settings.database.name = "test"
        mock_settings.database.user = "test"
        mock_settings.database.min_pool_size = 1
        mock_settings.database.max_pool_size = 5
        mock_settings.database.command_timeout = 5.0  # Short timeout for test
        mock_settings.database.ssl = False
        mock_settings.DATABASE_PASSWORD = "test"

        with (
            patch("app.database.connection.get_settings", return_value=mock_settings),
            pytest.raises(
                OSError, match=r"Name or service not known|nodename nor servname"
            ),
        ):
            await init_database_pool()
