"""Unit tests for shopping API routes."""

from http import HTTPStatus
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.routes.shopping import get_shopping_service, router
from app.api.v1.schemas.common.ingredient import Quantity
from app.services.shopping_service import ShoppingService
from tests.conftest import IsType


class TestShoppingRoutes:
    """Test suite for shopping API routes."""

    @pytest.mark.unit
    def test_get_shopping_service(self) -> None:
        """Test that get_shopping_service returns ShoppingService."""
        # Act
        service = get_shopping_service()

        # Assert
        assert isinstance(service, ShoppingService)

    @pytest.mark.unit
    def test_get_recipe_shopping_info(
        self,
        mock_shopping_service: Mock,
    ) -> None:
        """Test successful retrieval of shopping info for a recipe."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_shopping_service] = (
            lambda: mock_shopping_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        recipe_id = 1
        response = client.get(f"/recipe-scraper/recipes/{recipe_id}/shopping-info")

        # Assert
        mock_shopping_service.get_recipe_shopping_info.assert_called_once_with(
            recipe_id,
            IsType(Session),
        )
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.unit
    def test_get_ingredient_shopping_info(
        self,
        mock_shopping_service: Mock,
    ) -> None:
        """Test retrieval of shopping info for an ingredient."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_shopping_service] = (
            lambda: mock_shopping_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 1
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/shopping-info",
        )

        # Assert
        mock_shopping_service.get_ingredient_shopping_info.assert_called_once_with(
            ingredient_id,
            None,
            IsType(Session),
        )
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.unit
    def test_get_ingredient_shopping_info_with_quantity(
        self,
        mock_shopping_service: Mock,
        mock_quantity_schema: Quantity,
    ) -> None:
        """Test retrieval of shopping info for an ingredient with quantity."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_shopping_service] = (
            lambda: mock_shopping_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 2
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/shopping-info",
            params={
                "amount": mock_quantity_schema.amount,
                "measurement": mock_quantity_schema.measurement,
            },
        )

        # Assert
        mock_shopping_service.get_ingredient_shopping_info.assert_called_once_with(
            ingredient_id,
            mock_quantity_schema,
            IsType(Session),
        )
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.unit
    def test_get_ingredient_shopping_info_with_missing_measurement(
        self,
        mock_shopping_service: Mock,
        mock_quantity_schema: Quantity,
    ) -> None:
        """Test retrieval of shopping info with missing measurement parameter."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_shopping_service] = (
            lambda: mock_shopping_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 3
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/shopping-info",
            params={"amount": mock_quantity_schema.amount},
        )

        # Assert
        mock_shopping_service.get_ingredient_shopping_info.assert_not_called()
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.unit
    def test_get_ingredient_shopping_info_with_missing_amount(
        self,
        mock_shopping_service: Mock,
        mock_quantity_schema: Quantity,
    ) -> None:
        """Test retrieval of shopping info with missing amount parameter."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_shopping_service] = (
            lambda: mock_shopping_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 4
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/shopping-info",
            params={"measurement": mock_quantity_schema.measurement},
        )

        # Assert
        mock_shopping_service.get_ingredient_shopping_info.assert_not_called()
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.unit
    def test_get_ingredient_shopping_info_with_invalid_amount(
        self,
        mock_shopping_service: Mock,
        mock_quantity_schema: Quantity,
    ) -> None:
        """Test retrieval of shopping info with invalid amount parameter."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_shopping_service] = (
            lambda: mock_shopping_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 5
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/shopping-info",
            params={
                "amount": 0,
                "measurement": mock_quantity_schema.measurement,
            },
        )

        # Assert
        mock_shopping_service.get_ingredient_shopping_info.assert_not_called()
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    def test_get_ingredient_shopping_info_with_invalid_measurement(
        self,
        mock_shopping_service: Mock,
        mock_quantity_schema: Quantity,
    ) -> None:
        """Test retrieval of shopping info with invalid measurement parameter."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_shopping_service] = (
            lambda: mock_shopping_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 6
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/shopping-info",
            params={
                "amount": mock_quantity_schema.amount,
                "measurement": "invalid",
            },
        )

        # Assert
        mock_shopping_service.get_ingredient_shopping_info.assert_not_called()
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
