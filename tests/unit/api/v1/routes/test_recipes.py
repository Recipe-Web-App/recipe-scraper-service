"""Unit tests for recipe API routes."""

from http import HTTPStatus
from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.routes.recipes import get_recipe_scraper_service, router
from app.api.v1.schemas.common.pagination_params import PaginationParams
from app.api.v1.schemas.request.create_recipe_request import CreateRecipeRequest
from app.services.recipe_scraper_service import RecipeScraperService
from tests.conftest import IsType


class TestRecipesRoutes:
    """Test suite for recipe API routes."""

    @pytest.mark.unit
    def test_get_recipe_scraper_service(self) -> None:
        """Test that get_recipe_scraper_service returns RecipeScraperService."""
        # Act
        service = get_recipe_scraper_service()

        # Assert
        assert isinstance(service, RecipeScraperService)

    @pytest.mark.unit
    def test_create_recipe(
        self,
        mock_recipe_scraper_service: Mock,
        mock_user_id: UUID,
        mock_create_recipe_request: CreateRecipeRequest,
    ) -> None:
        """Test successful creation of a recipe."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recipe_scraper_service] = (
            lambda: mock_recipe_scraper_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        response = client.post(
            "/recipe-scraper/create-recipe",
            json=mock_create_recipe_request.model_dump(),
            headers={"X-User-ID": str(mock_user_id)},
        )

        # Assert
        mock_recipe_scraper_service.create_recipe.assert_called_once_with(
            mock_create_recipe_request.recipe_url,
            IsType(Session),
            mock_user_id,
        )
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.unit
    def test_get_popular_recipes(self, mock_recipe_scraper_service: Mock) -> None:
        """Test successful retrieval of popular recipes."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recipe_scraper_service] = (
            lambda: mock_recipe_scraper_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        response = client.get("/recipe-scraper/popular-recipes")

        # Assert
        default_pagination_params = PaginationParams(
            limit=50,
            offset=0,
            count_only=False,
        )
        mock_recipe_scraper_service.get_popular_recipes.assert_called_once_with(
            default_pagination_params,
        )
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.unit
    def test_get_popular_recipes_with_pagination(
        self,
        mock_recipe_scraper_service: Mock,
        mock_pagination_params: PaginationParams,
    ) -> None:
        """Test retrieval of popular recipes with pagination parameters."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recipe_scraper_service] = (
            lambda: mock_recipe_scraper_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        response = client.get(
            "/recipe-scraper/popular-recipes",
            params={
                "limit": mock_pagination_params.limit,
                "offset": mock_pagination_params.offset,
                "count_only": mock_pagination_params.count_only,
            },
        )

        # Assert
        mock_recipe_scraper_service.get_popular_recipes.assert_called_once_with(
            mock_pagination_params,
        )
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.unit
    def test_get_popular_recipes_with_count_only_pagination_parameter(
        self,
        mock_recipe_scraper_service: Mock,
        mock_pagination_params_count_only: PaginationParams,
    ) -> None:
        """Test retrieval of popular recipes with count_only pagination parameter."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recipe_scraper_service] = (
            lambda: mock_recipe_scraper_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        response = client.get(
            "/recipe-scraper/popular-recipes",
            params={
                "count_only": mock_pagination_params_count_only.count_only,
            },
        )

        # Assert
        mock_recipe_scraper_service.get_popular_recipes.assert_called_once_with(
            mock_pagination_params_count_only,
        )
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.unit
    def test_get_popular_recipes_with_invalid_pagination_parameters(
        self,
        mock_recipe_scraper_service: Mock,
        mock_pagination_params_invalid_range: PaginationParams,
    ) -> None:
        """Test retrieval of popular recipes with invalid pagination parameters."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recipe_scraper_service] = (
            lambda: mock_recipe_scraper_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        response = client.get(
            "/recipe-scraper/popular-recipes",
            params={
                "limit": mock_pagination_params_invalid_range.limit,
                "offset": mock_pagination_params_invalid_range.offset,
                "count_only": mock_pagination_params_invalid_range.count_only,
            },
        )

        # Assert
        mock_recipe_scraper_service.get_popular_recipes.assert_not_called()
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.unit
    def test_get_popular_recipes_with_invalid_limit_parameter(
        self,
        mock_recipe_scraper_service: Mock,
        mock_pagination_params: PaginationParams,
    ) -> None:
        """Test retrieval of popular recipes with invalid limit parameter."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recipe_scraper_service] = (
            lambda: mock_recipe_scraper_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        response = client.get(
            "/recipe-scraper/popular-recipes",
            params={
                "limit": -1,
                "offset": mock_pagination_params.offset,
                "count_only": mock_pagination_params.count_only,
            },
        )

        # Assert
        mock_recipe_scraper_service.get_popular_recipes.assert_not_called()
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    def test_get_popular_recipes_with_invalid_offset_parameter(
        self,
        mock_recipe_scraper_service: Mock,
        mock_pagination_params: PaginationParams,
    ) -> None:
        """Test retrieval of popular recipes with invalid offset parameter."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recipe_scraper_service] = (
            lambda: mock_recipe_scraper_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        response = client.get(
            "/recipe-scraper/popular-recipes",
            params={
                "limit": mock_pagination_params.limit,
                "offset": -1,
                "count_only": mock_pagination_params.count_only,
            },
        )

        # Assert
        mock_recipe_scraper_service.get_popular_recipes.assert_not_called()
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    def test_get_popular_recipes_with_invalid_count_only_parameter(
        self,
        mock_recipe_scraper_service: Mock,
        mock_pagination_params: PaginationParams,
    ) -> None:
        """Test retrieval of popular recipes with invalid count_only parameter."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recipe_scraper_service] = (
            lambda: mock_recipe_scraper_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        response = client.get(
            "/recipe-scraper/popular-recipes",
            params={
                "limit": mock_pagination_params.limit,
                "offset": mock_pagination_params.offset,
                "count_only": "invalid",
            },
        )

        # Assert
        mock_recipe_scraper_service.get_popular_recipes.assert_not_called()
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
