"""Database unit test fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.database.connection as db_module


if TYPE_CHECKING:
    from collections.abc import Generator

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def reset_database_globals() -> Generator[None]:
    """Reset database global state before and after each test."""
    db_module._pool = None
    yield
    db_module._pool = None


@pytest.fixture
def mock_pool() -> MagicMock:
    """Create a mock asyncpg pool."""
    pool = MagicMock()
    pool.close = AsyncMock()

    # Mock connection context manager
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.fetch = AsyncMock(return_value=[])

    pool.acquire = MagicMock(return_value=AsyncMock())
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    return pool
