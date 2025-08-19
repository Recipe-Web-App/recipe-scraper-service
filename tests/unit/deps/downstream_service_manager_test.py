"""Unit tests for the downstream service manager."""

from unittest.mock import Mock, patch

import pytest

from app.deps.downstream_service_manager import (
    _DownstreamServiceManager,
    get_downstream_service_manager,
)
from app.services.downstream.spoonacular_service import SpoonacularService


class TestDownstreamServiceManager:
    """Unit tests for the _DownstreamServiceManager class."""

    @pytest.mark.unit
    def test_manager_initialization(self) -> None:
        """Test that manager initializes with empty services dict."""
        # Act
        manager = _DownstreamServiceManager()

        # Assert
        assert manager._services == {}

    @pytest.mark.unit
    def test_get_service_creates_new_instance(self) -> None:
        """Test that get_service creates a new instance when none exists."""
        # Arrange
        manager = _DownstreamServiceManager()
        mock_service_class = Mock()
        mock_service_class.__name__ = "MockService"  # Add __name__ attribute
        mock_instance = Mock()
        mock_service_class.return_value = mock_instance

        # Act
        result: Mock = manager.get_service(mock_service_class)

        # Assert
        assert result == mock_instance
        mock_service_class.assert_called_once()
        assert mock_service_class in manager._services

    @pytest.mark.unit
    def test_get_service_returns_existing_instance(self) -> None:
        """Test that get_service returns existing instance when available."""
        # Arrange
        manager = _DownstreamServiceManager()
        mock_service_class = Mock()
        mock_service_class.__name__ = "MockService"  # Add __name__ attribute
        mock_instance = Mock()
        manager._services[mock_service_class] = mock_instance

        # Act
        result: Mock = manager.get_service(mock_service_class)

        # Assert
        assert result == mock_instance
        # Should not create a new instance
        mock_service_class.assert_not_called()

    @pytest.mark.unit
    @patch("app.deps.downstream_service_manager.SpoonacularService")
    def test_get_spoonacular_service(self, mock_spoonacular_class: Mock) -> None:
        """Test that get_spoonacular_service returns SpoonacularService instance."""
        # Arrange
        manager = _DownstreamServiceManager()
        mock_spoonacular_class.__name__ = "SpoonacularService"  # Add __name__ attribute
        mock_instance = Mock(spec=SpoonacularService)
        mock_spoonacular_class.return_value = mock_instance

        # Act
        result = manager.get_spoonacular_service()

        # Assert
        assert result == mock_instance
        mock_spoonacular_class.assert_called_once()

    @pytest.mark.unit
    def test_close_all_calls_close_methods(self) -> None:
        """Test that close_all calls close methods on services that have them."""
        # Arrange
        manager = _DownstreamServiceManager()
        mock_service_with_close = Mock()
        mock_service_with_close.close = Mock()
        mock_service_class = Mock()
        mock_service_class.__name__ = "MockService"  # Add __name__ attribute
        manager._services[mock_service_class] = mock_service_with_close

        # Act
        manager.close_all()

        # Assert
        mock_service_with_close.close.assert_called_once()
        assert manager._services == {}

    @pytest.mark.unit
    def test_close_all_calls_del_methods_when_no_close(self) -> None:
        """Test that close_all calls __del__ when close method doesn't exist."""
        # Arrange
        manager = _DownstreamServiceManager()

        # Create a custom mock class that supports __del__
        class MockServiceWithDel:
            def __init__(self) -> None:
                self.del_called = False

            def __del__(self) -> None:
                self.del_called = True

        mock_service_with_del: MockServiceWithDel = MockServiceWithDel()
        mock_service_class = Mock()
        mock_service_class.__name__ = "MockServiceWithDel"
        manager._services[mock_service_class] = mock_service_with_del

        # Act
        manager.close_all()

        # Assert
        # We can't directly assert on __del__ being called, but we can check
        # that the service was removed from the dict
        assert manager._services == {}

    @pytest.mark.unit
    def test_close_all_handles_exceptions_gracefully(self) -> None:
        """Test that close_all handles exceptions during cleanup gracefully."""
        # Arrange
        manager = _DownstreamServiceManager()
        mock_service = Mock()
        mock_service.close.side_effect = RuntimeError("Close failed")
        mock_service_class = Mock()
        mock_service_class.__name__ = "MockService"  # Add __name__ attribute
        manager._services[mock_service_class] = mock_service

        # Act & Assert - Should not raise an exception
        manager.close_all()
        assert manager._services == {}

    @pytest.mark.unit
    def test_close_all_with_no_cleanup_methods(self) -> None:
        """Test that close_all works with services that have no cleanup methods."""
        # Arrange
        manager = _DownstreamServiceManager()
        mock_service = Mock(spec=[])  # No close or __del__ methods
        mock_service_class = Mock()
        mock_service_class.__name__ = "MockService"  # Add __name__ attribute
        manager._services[mock_service_class] = mock_service

        # Act & Assert - Should not raise an exception
        manager.close_all()
        assert manager._services == {}

    @pytest.mark.unit
    def test_del_calls_close_all(self) -> None:
        """Test that __del__ calls close_all."""
        # Arrange
        manager = _DownstreamServiceManager()
        # We can't directly mock close_all method, so we'll test indirectly
        # by adding a service and checking it gets cleaned up
        mock_service = Mock()
        mock_service.close = Mock()
        mock_service_class = Mock()
        mock_service_class.__name__ = "MockService"
        manager._services[mock_service_class] = mock_service

        # Act
        manager.__del__()

        # Assert - check that services were cleaned up (close_all was called)
        assert manager._services == {}


class TestGetDownstreamServiceManager:
    """Unit tests for the get_downstream_service_manager function."""

    @pytest.mark.unit
    def test_get_downstream_service_manager_returns_instance(self) -> None:
        """Test that get_downstream_service_manager returns a manager instance."""
        # Act
        result = get_downstream_service_manager()

        # Assert
        assert isinstance(result, _DownstreamServiceManager)

    @pytest.mark.unit
    def test_get_downstream_service_manager_returns_same_instance(self) -> None:
        """Test that get_downstream_service_manager returns same instance."""
        # Act
        result1 = get_downstream_service_manager()
        result2 = get_downstream_service_manager()

        # Assert
        assert result1 is result2

    @pytest.mark.unit
    def test_get_downstream_service_manager_cache_cleared(self) -> None:
        """Test behavior when cache is cleared."""
        # Arrange
        first_manager = get_downstream_service_manager()

        # Clear the cache
        get_downstream_service_manager.cache_clear()

        # Act
        second_manager = get_downstream_service_manager()

        # Assert
        assert first_manager is not second_manager
        assert isinstance(second_manager, _DownstreamServiceManager)
