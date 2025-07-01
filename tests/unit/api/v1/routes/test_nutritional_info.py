"""Unit tests for the nutritional info API routes."""

from http import HTTPStatus
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.routes.nutritional_info import get_nutritional_info_service, router
from app.api.v1.schemas.common.ingredient import Quantity
from app.api.v1.schemas.response.recipe_nutritional_info_response import (
    RecipeNutritionalInfoResponse,
)
from app.services.nutritional_info_service import NutritionalInfoService
from tests.conftest import IsType


class TestNutritionalInfoRoutes:
    """Test suite for nutritional info API routes."""

    @pytest.mark.unit
    def test_get_nutritional_info_service(self) -> None:
        """Test that get_nutritional_info_service returns NutritionalInfoService."""
        # Act
        service = get_nutritional_info_service()

        # Assert
        assert isinstance(service, NutritionalInfoService)

    @pytest.mark.unit
    def test_get_recipe_nutritional_info(
        self,
        mock_nutritional_info_service: Mock,
    ) -> None:
        """Test successful retrieval of nutritional info for a recipe."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_nutritional_info_service] = (
            lambda: mock_nutritional_info_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        recipe_id = 1
        response = client.get(f"/recipe-scraper/recipes/{recipe_id}/nutritional-info")

        # Assert
        mock_nutritional_info_service.get_recipe_nutritional_info.assert_called_once_with(
            recipe_id,
            True,
            False,
            IsType(Session),
        )
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.unit
    def test_get_recipe_nutritional_info_with_params(
        self,
        mock_nutritional_info_service: Mock,
    ) -> None:
        """Test retrieval of nutritional info for a recipe with query params."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_nutritional_info_service] = (
            lambda: mock_nutritional_info_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        recipe_id = 2
        response = client.get(
            f"/recipe-scraper/recipes/{recipe_id}/nutritional-info",
            params={
                "include_total": False,
                "include_ingredients": True,
            },
        )

        # Assert
        mock_nutritional_info_service.get_recipe_nutritional_info.assert_called_once_with(
            recipe_id,
            False,
            True,
            IsType(Session),
        )
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.unit
    def test_get_recipe_nutritional_info_invalid_params(
        self,
        mock_nutritional_info_service: Mock,
    ) -> None:
        """Test retrieval of nutritional info with invalid query params."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_nutritional_info_service] = (
            lambda: mock_nutritional_info_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        recipe_id = 3
        response = client.get(
            f"/recipe-scraper/recipes/{recipe_id}/nutritional-info",
            params={
                "include_total": "False",
                "include_ingredients": "False",
            },
        )

        # Assert
        mock_nutritional_info_service.get_recipe_nutritional_info.assert_not_called()
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.unit
    def test_get_recipe_nutritional_info_with_missing_ingredients(
        self,
        mock_nutritional_info_service: Mock,
        mock_recipe_nutritional_info_response_with_missing_ingredients: (
            RecipeNutritionalInfoResponse
        ),
    ) -> None:
        """Test retrieval of nutritional info for a recipe with missing ingredients."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_nutritional_info_service] = (
            lambda: mock_nutritional_info_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        mock_nutritional_info_service.get_recipe_nutritional_info.return_value = (
            mock_recipe_nutritional_info_response_with_missing_ingredients
        )

        # Act
        recipe_id = 4
        response = client.get(f"/recipe-scraper/recipes/{recipe_id}/nutritional-info")

        # Assert
        mock_nutritional_info_service.get_recipe_nutritional_info.assert_called_once_with(
            recipe_id,
            True,
            False,
            IsType(Session),
        )
        assert response.status_code == HTTPStatus.PARTIAL_CONTENT
        expected = jsonable_encoder(
            mock_recipe_nutritional_info_response_with_missing_ingredients,
            by_alias=False,
        )
        assert response.json() == expected

    @pytest.mark.unit
    def test_get_ingredient_nutritional_info(
        self,
        mock_nutritional_info_service: Mock,
    ) -> None:
        """Test retrieval of nutritional info for an ingredient."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_nutritional_info_service] = (
            lambda: mock_nutritional_info_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 1
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/nutritional-info",
        )

        # Assert
        mock_nutritional_info_service.get_ingredient_nutritional_info.assert_called_once_with(
            ingredient_id,
            None,
            IsType(Session),
        )
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.unit
    def test_get_ingredient_nutritional_info_with_quantity_query_params(
        self,
        mock_nutritional_info_service: Mock,
        mock_quantity: Quantity,
    ) -> None:
        """Test retrieval of nutritional info for an ingredient with quantity."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_nutritional_info_service] = (
            lambda: mock_nutritional_info_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 2
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/nutritional-info",
            params={
                "amount": mock_quantity.amount,
                "measurement": mock_quantity.measurement,
            },
        )

        # Assert
        mock_nutritional_info_service.get_ingredient_nutritional_info.assert_called_once_with(
            ingredient_id,
            mock_quantity,
            IsType(Session),
        )
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.unit
    def test_get_ingredient_nutritional_info_with_missing_measurement_parameter(
        self,
        mock_nutritional_info_service: Mock,
        mock_quantity: Quantity,
    ) -> None:
        """Test retrieval of nutritional info with missing measurement parameter."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_nutritional_info_service] = (
            lambda: mock_nutritional_info_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 3
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/nutritional-info",
            params={"amount": mock_quantity.amount},
        )

        # Assert
        mock_nutritional_info_service.get_ingredient_nutritional_info.assert_not_called()
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.unit
    def test_get_ingredient_nutritional_info_with_missing_amount_parameter(
        self,
        mock_nutritional_info_service: Mock,
        mock_quantity: Quantity,
    ) -> None:
        """Test retrieval of nutritional info with missing amount parameter."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_nutritional_info_service] = (
            lambda: mock_nutritional_info_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 4
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/nutritional-info",
            params={"measurement": mock_quantity.measurement},
        )

        # Assert
        mock_nutritional_info_service.get_ingredient_nutritional_info.assert_not_called()
        assert response.status_code == HTTPStatus.BAD_REQUEST
