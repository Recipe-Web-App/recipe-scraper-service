"""Shared test fixtures and configuration for the Recipe Scraper service tests.

This module provides pytest fixtures that are used across multiple test modules,
including database setup, mock services, and test client configuration.
"""

from unittest.mock import Mock

import pytest

from app.services.admin_service import AdminService


@pytest.fixture
def mock_admin_service() -> Mock:
    """Create a mock AdminService for testing.

    Returns:
        Mock: Mocked AdminService instance
    """
    mock_service = Mock(spec=AdminService)
    mock_service.clear_cache.return_value = None
    return mock_service


@pytest.fixture
def mock_cache_manager() -> Mock:
    """Create a mock CacheManager for testing.

    Returns:
        Mock: Mocked CacheManager instance
    """
    mock_cache = Mock()
    mock_cache.clear_all.return_value = None
    return mock_cache
