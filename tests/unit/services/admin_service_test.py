"""Unit tests for AdminService.

This module contains comprehensive unit tests for the AdminService class, testing
administrative functionality including cache management operations.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.admin_service import AdminService


@pytest.mark.unit
class TestAdminService:
    """Unit tests for AdminService."""

    def test_admin_service_initialization(self) -> None:
        """Test AdminService initialization."""
        # Arrange & Act
        with patch("app.services.admin_service.get_cache_manager") as mock_get_cache:
            mock_cache_manager = Mock()
            mock_get_cache.return_value = mock_cache_manager

            admin_service = AdminService()

        # Assert
        assert admin_service is not None
        assert admin_service._cache_manager == mock_cache_manager
        mock_get_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_cache_success(self) -> None:
        """Test successful cache clearing."""
        # Arrange
        with patch("app.services.admin_service.get_cache_manager") as mock_get_cache:
            mock_cache_manager = AsyncMock()
            mock_get_cache.return_value = mock_cache_manager
            admin_service = AdminService()

        # Act
        await admin_service.clear_cache()

        # Assert
        mock_cache_manager.clear_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_cache_with_exception_propagation(self) -> None:
        """Test cache clearing propagates exceptions from cache manager."""
        # Arrange
        with patch("app.services.admin_service.get_cache_manager") as mock_get_cache:
            mock_cache_manager = AsyncMock()
            mock_cache_manager.clear_all.side_effect = Exception("Cache error")
            mock_get_cache.return_value = mock_cache_manager
            admin_service = AdminService()

        # Act & Assert - Should raise exception
        with pytest.raises(Exception, match="Cache error"):
            await admin_service.clear_cache()

        # Verify the cache manager was called
        mock_cache_manager.clear_all.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.admin_service._log")
    async def test_clear_cache_logging(self, mock_logger: Mock) -> None:
        """Test that cache clearing logs success message."""
        # Arrange
        with patch("app.services.admin_service.get_cache_manager") as mock_get_cache:
            mock_cache_manager = AsyncMock()
            mock_get_cache.return_value = mock_cache_manager
            admin_service = AdminService()

        # Act
        await admin_service.clear_cache()

        # Assert
        mock_logger.info.assert_called_once_with(
            "Successfully cleared Recipe Scraper service cache"
        )

    @pytest.mark.asyncio
    @patch("app.services.admin_service._log")
    async def test_clear_cache_exception_prevents_logging(
        self, mock_logger: Mock
    ) -> None:
        """Test that exceptions during cache clearing prevent success logging."""
        # Arrange
        with patch("app.services.admin_service.get_cache_manager") as mock_get_cache:
            mock_cache_manager = AsyncMock()
            mock_cache_manager.clear_all.side_effect = Exception("Cache error")
            mock_get_cache.return_value = mock_cache_manager
            admin_service = AdminService()

        # Act & Assert
        with pytest.raises(Exception, match="Cache error"):
            await admin_service.clear_cache()

        # Assert - Success message should not be logged when exception occurs
        mock_logger.info.assert_not_called()

    def test_admin_service_cache_manager_property_access(self) -> None:
        """Test accessing the cache manager property."""
        # Arrange
        with patch("app.services.admin_service.get_cache_manager") as mock_get_cache:
            mock_cache_manager = Mock()
            mock_get_cache.return_value = mock_cache_manager
            admin_service = AdminService()

        # Act & Assert
        assert admin_service._cache_manager is mock_cache_manager

    @pytest.mark.asyncio
    async def test_clear_cache_idempotent_behavior(self) -> None:
        """Test that multiple cache clear calls work correctly."""
        # Arrange
        with patch("app.services.admin_service.get_cache_manager") as mock_get_cache:
            mock_cache_manager = AsyncMock()
            mock_get_cache.return_value = mock_cache_manager
            admin_service = AdminService()

        # Act - Call clear_cache multiple times
        await admin_service.clear_cache()
        await admin_service.clear_cache()
        await admin_service.clear_cache()

        # Assert - Should be called three times
        assert mock_cache_manager.clear_all.call_count == 3

    def test_admin_service_singleton_behavior(self) -> None:
        """Test that each AdminService instance gets its own cache manager."""
        # Arrange & Act
        with patch("app.services.admin_service.get_cache_manager") as mock_get_cache:
            mock_cache_manager_1 = Mock()
            mock_cache_manager_2 = Mock()
            mock_get_cache.side_effect = [mock_cache_manager_1, mock_cache_manager_2]

            admin_service_1 = AdminService()
            admin_service_2 = AdminService()

        # Assert
        assert admin_service_1._cache_manager == mock_cache_manager_1
        assert admin_service_2._cache_manager == mock_cache_manager_2
        assert admin_service_1._cache_manager != admin_service_2._cache_manager
        assert mock_get_cache.call_count == 2

    @pytest.mark.asyncio
    async def test_clear_cache_async_operation(self) -> None:
        """Test that clear_cache properly handles async operations."""
        # Arrange
        with patch("app.services.admin_service.get_cache_manager") as mock_get_cache:
            mock_cache_manager = AsyncMock()

            # Make clear_all return a coroutine that takes some time
            async def slow_clear() -> None:
                return None

            mock_cache_manager.clear_all = AsyncMock(side_effect=slow_clear)
            mock_get_cache.return_value = mock_cache_manager
            admin_service = AdminService()

        # Act
        result = await admin_service.clear_cache()  # type: ignore

        # Assert
        assert result is None
        mock_cache_manager.clear_all.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.admin_service._log")
    async def test_clear_cache_logging_with_different_cache_managers(
        self, mock_logger: Mock
    ) -> None:
        """Test logging works correctly with different cache manager instances."""
        # Arrange
        with patch("app.services.admin_service.get_cache_manager") as mock_get_cache:
            mock_cache_manager_1 = AsyncMock()
            mock_cache_manager_2 = AsyncMock()
            mock_get_cache.side_effect = [mock_cache_manager_1, mock_cache_manager_2]

            admin_service_1 = AdminService()
            admin_service_2 = AdminService()

        # Act
        await admin_service_1.clear_cache()
        await admin_service_2.clear_cache()

        # Assert
        assert mock_logger.info.call_count == 2
        expected_message = "Successfully cleared Recipe Scraper service cache"
        mock_logger.info.assert_any_call(expected_message)

    def test_admin_service_docstring_and_attributes(self) -> None:
        """Test AdminService has proper documentation and attributes."""
        # Assert class docstring exists
        assert AdminService.__doc__ is not None
        assert "Admin Service" in AdminService.__doc__
        assert "cache management" in AdminService.__doc__

        # Assert init method docstring exists
        assert AdminService.__init__.__doc__ is not None

        # Assert clear_cache method docstring exists
        assert AdminService.clear_cache.__doc__ is not None
        assert "Clear the cache" in AdminService.clear_cache.__doc__
        assert "administrative use only" in AdminService.clear_cache.__doc__
