"""Unit tests for admin API routes.

This module contains comprehensive unit tests for the administrative API endpoints,
including cache clearing and dependency injection testing.
"""

from http import HTTPStatus
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.routes.admin import get_admin_service, router
from app.services.admin_service import AdminService


class TestAdminRoutes:
    """Test suite for admin API routes."""

    @pytest.mark.unit
    def test_get_admin_service_dependency(self) -> None:
        """Test that get_admin_service returns AdminService instance."""
        # Act
        service = get_admin_service()

        # Assert
        assert isinstance(service, AdminService)

    @pytest.mark.unit
    def test_clear_cache_success(
        self,
        mock_admin_service: Mock,
    ) -> None:
        """Test successful cache clearing endpoint.

        Args:     mock_admin_service: Mocked admin service
        """
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_admin_service] = lambda: mock_admin_service
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        response = client.post("/recipe-scraper/admin/clear-cache")

        # Assert
        mock_admin_service.clear_cache.assert_called_once()
        assert response.status_code == HTTPStatus.OK
