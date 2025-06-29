"""Unit tests for the nutritional info API routes."""

from http import HTTPStatus
from unittest.mock import ANY, Mock

import pytest
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient

from app.api.v1.routes.nutritional_info import get_nutritional_info_service, router
from app.api.v1.schemas.common.ingredient import Quantity
from app.api.v1.schemas.response.recipe_nutritional_info_response import (
    RecipeNutritionalInfoResponse,
)
from app.services.nutritional_info_service import NutritionalInfoService


class TestNutritionalInfoRoutes:
    """Test suite for nutritional info API routes."""

    @pytest.mark.unit
    def test_get_nutritional_info_service_dependency(self) -> None:
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
        response = client.get("/recipe-scraper/recipes/1/nutritional-info")

        # Assert
        mock_nutritional_info_service.get_recipe_nutritional_info.assert_called_once_with(
            1,
            True,
            False,
            ANY,
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
        response = client.get(
            "/recipe-scraper/recipes/1/nutritional-info",
            params={
                "include_total": False,
                "include_ingredients": True,
            },
        )

        # Assert
        mock_nutritional_info_service.get_recipe_nutritional_info.assert_called_once_with(
            1,
            False,
            True,
            ANY,
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
        response = client.get(
            "/recipe-scraper/recipes/2/nutritional-info",
            params={
                "include_total": "False",
                "include_ingredients": "False",
            },
        )

        # Assert
        assert mock_nutritional_info_service.get_recipe_nutritional_info.call_count == 0
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
        response = client.get("/recipe-scraper/recipes/3/nutritional-info")

        # Assert
        mock_nutritional_info_service.get_recipe_nutritional_info.assert_called_once_with(
            3,
            True,
            False,
            ANY,
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
        response = client.get("/recipe-scraper/ingredients/1/nutritional-info")

        # Assert
        mock_nutritional_info_service.get_ingredient_nutritional_info.assert_called_once_with(
            1,
            None,
            ANY,
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
        response = client.get(
            "/recipe-scraper/ingredients/1/nutritional-info",
            params={
                "amount": mock_quantity.amount,
                "measurement": mock_quantity.measurement,
            },
        )

        # Assert
        mock_nutritional_info_service.get_ingredient_nutritional_info.assert_called_once_with(
            1,
            mock_quantity,
            ANY,
        )
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.unit
    def test_get_ingredient_nutritional_info_with_invalid_quantity(
        self,
        mock_nutritional_info_service: Mock,
    ) -> None:
        """Test retrieval of nutritional info with invalid quantity."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_nutritional_info_service] = (
            lambda: mock_nutritional_info_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        response = client.get(
            "/recipe-scraper/ingredients/1/nutritional-info",
            params={"amount": "1"},
        )

        # Assert
        assert (
            mock_nutritional_info_service.get_ingredient_nutritional_info.call_count
            == 0
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST
