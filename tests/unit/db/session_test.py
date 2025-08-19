"""Unit tests for the database session management."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db


class TestSession:
    """Unit tests for the database session functionality."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_db_yields_session(self) -> None:
        """Test that get_db yields an AsyncSession instance."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)

        # Create a proper async context manager mock
        async_context_manager = MagicMock()
        async_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
        async_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_async_session_local = MagicMock(return_value=async_context_manager)

        # Act & Assert
        with patch("app.db.session.AsyncSessionLocal", mock_async_session_local):
            async_generator = get_db()
            session = await async_generator.__anext__()

            assert session == mock_session
            mock_async_session_local.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_db_closes_session(self) -> None:
        """Test that get_db properly closes the session."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)

        # Create a proper async context manager mock
        async_context_manager = MagicMock()
        async_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
        async_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_async_session_local = MagicMock(return_value=async_context_manager)

        # Act
        with patch("app.db.session.AsyncSessionLocal", mock_async_session_local):
            async_generator = get_db()
            await async_generator.__anext__()

            # Simulate completion by exhausting the generator
            try:
                await async_generator.__anext__()
            except StopAsyncIteration:
                pass

            # Assert - the session close is handled by the context manager's __aexit__
            async_context_manager.__aexit__.assert_called_once()
