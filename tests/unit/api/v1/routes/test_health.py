"""Unit tests for admin API routes.

This module contains comprehensive unit tests for the health check API endpoints,
"""

from http import HTTPStatus

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.routes.health import router


class TestHealthRoutes:
    """Test suite for health check API routes."""

    @pytest.mark.unit
    def test_health_check(self) -> None:
        """Test that the health check endpoint returns 200 OK and correct JSON."""
        # Arrange
        test_app = FastAPI()
        test_app.include_router(router)

        client = TestClient(test_app)

        # Act
        response = client.get("/recipe-scraper/health")

        # Assert
        assert response.status_code == HTTPStatus.OK
        expected_response = {"status": "ok"}
        assert response.json() == expected_response
