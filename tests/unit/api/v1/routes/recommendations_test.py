"""Unit tests for recommendations API routes."""

from http import HTTPStatus
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.routes.recommendations import get_recommendations_service, router
from app.api.v1.schemas.common.ingredient import Quantity
from app.api.v1.schemas.common.pagination_params import PaginationParams
from app.services.recommendations_service import RecommendationsService
from tests.conftest import IsType


class TestRecommendationsRoutes:
    """Test suite for recommendations API routes."""

    @pytest.mark.unit
    def test_get_recommendations_service(self) -> None:
        """Test that get_recommendations_service returns RecommendationsService."""
        # Act
        service = get_recommendations_service()

        # Assert
        assert isinstance(service, RecommendationsService)

    @pytest.mark.unit
    def test_get_recommended_substitutions(
        self,
        mock_recommendations_service: Mock,
        default_pagination_params_schema: PaginationParams,
    ) -> None:
        """Test retrieval of recommended substitutions."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recommendations_service] = (
            lambda: mock_recommendations_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 1
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/recommended-substitutions",
        )

        # Assert
        mock_recommendations_service.get_recommended_substitutions.assert_called_once_with(
            ingredient_id,
            None,
            default_pagination_params_schema,
            IsType(Session),
        )
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.unit
    def test_get_recommended_substitutions_with_quantity_parameters(
        self,
        mock_recommendations_service: Mock,
        mock_quantity_schema: Quantity,
    ) -> None:
        """Test retrieval of recommended substitutions with Quantity parameters."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recommendations_service] = (
            lambda: mock_recommendations_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 2
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/recommended-substitutions",
            params={
                "amount": mock_quantity_schema.amount,
                "measurement": mock_quantity_schema.measurement,
            },
        )

        # Assert
        default_pagination_params = PaginationParams(
            limit=50,
            offset=0,
            count_only=False,
        )
        mock_recommendations_service.get_recommended_substitutions.assert_called_once_with(
            ingredient_id,
            mock_quantity_schema,
            default_pagination_params,
            IsType(Session),
        )
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.unit
    def test_get_recommended_substitutions_with_missing_amount_parameter(
        self,
        mock_recommendations_service: Mock,
        mock_quantity_schema: Quantity,
    ) -> None:
        """Test retrieval of recommended substitutions with no amount param."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recommendations_service] = (
            lambda: mock_recommendations_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 3
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/recommended-substitutions",
            params={"measurement": mock_quantity_schema.measurement},
        )

        # Assert
        mock_recommendations_service.get_recommended_substitutions.assert_not_called()
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.unit
    def test_get_recommended_substitutions_with_invalid_amount_parameter(
        self,
        mock_recommendations_service: Mock,
        mock_quantity_schema: Quantity,
    ) -> None:
        """Test retrieval of recommended substitutions with an invalid amount param."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recommendations_service] = (
            lambda: mock_recommendations_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 4
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/recommended-substitutions",
            params={
                "amount": 0,
                "measurement": mock_quantity_schema.measurement,
            },
        )

        # Assert
        mock_recommendations_service.get_recommended_substitutions.assert_not_called()
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    def test_get_recommended_substitutions_with_missing_measurement_parameter(
        self,
        mock_recommendations_service: Mock,
        mock_quantity_schema: Quantity,
    ) -> None:
        """Test retrieval of recommended substitutions with no measurement param."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recommendations_service] = (
            lambda: mock_recommendations_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 5
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/recommended-substitutions",
            params={"amount": mock_quantity_schema.amount},
        )

        # Assert
        mock_recommendations_service.get_recommended_substitutions.assert_not_called()
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.unit
    def test_get_recommended_substitutions_with_invalid_measurement_parameter(
        self,
        mock_recommendations_service: Mock,
        mock_quantity_schema: Quantity,
    ) -> None:
        """Test retrieval of recommended substitutions with an invalid measurement."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recommendations_service] = (
            lambda: mock_recommendations_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 6
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/recommended-substitutions",
            params={"amount": mock_quantity_schema.amount, "measurement": "invalid"},
        )

        # Assert
        mock_recommendations_service.get_recommended_substitutions.assert_not_called()
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    def test_get_recommended_substitutions_with_pagination_parameters(
        self,
        mock_recommendations_service: Mock,
        mock_pagination_params_schema: PaginationParams,
    ) -> None:
        """Test retrieval of recommended substitutions with pagination."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recommendations_service] = (
            lambda: mock_recommendations_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 7
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/recommended-substitutions",
            params={
                "limit": mock_pagination_params_schema.limit,
                "offset": mock_pagination_params_schema.offset,
                "count_only": mock_pagination_params_schema.count_only,
            },
        )

        # Assert
        mock_recommendations_service.get_recommended_substitutions.assert_called_once_with(
            ingredient_id,
            None,
            mock_pagination_params_schema,
            IsType(Session),
        )
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.unit
    def test_get_recommended_substitutions_with_count_only_pagination_parameter(
        self,
        mock_recommendations_service: Mock,
        mock_pagination_params_schema_count_only: PaginationParams,
    ) -> None:
        """Test retrieval of recommended substitutions with count only pagination."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recommendations_service] = (
            lambda: mock_recommendations_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 8
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/recommended-substitutions",
            params={
                "count_only": mock_pagination_params_schema_count_only.count_only,
            },
        )

        # Assert
        mock_recommendations_service.get_recommended_substitutions.assert_called_once_with(
            ingredient_id,
            None,
            mock_pagination_params_schema_count_only,
            IsType(Session),
        )
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.unit
    def test_get_recommended_substitutions_with_invalid_pagination_parameters(
        self,
        mock_recommendations_service: Mock,
        mock_pagination_params_schema_invalid_range: PaginationParams,
    ) -> None:
        """Test retrieval of recommended substitutions with invalid pagination param."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recommendations_service] = (
            lambda: mock_recommendations_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 8
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/recommended-substitutions",
            params={
                "limit": mock_pagination_params_schema_invalid_range.limit,
                "offset": mock_pagination_params_schema_invalid_range.offset,
            },
        )

        # Assert
        mock_recommendations_service.get_recommended_substitutions.assert_not_called()
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.unit
    def test_get_recommended_substitutions_with_invalid_limit_parameter(
        self,
        mock_recommendations_service: Mock,
        mock_pagination_params_schema: PaginationParams,
    ) -> None:
        """Test retrieval of recommended substitutions with invalid limit parameter."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recommendations_service] = (
            lambda: mock_recommendations_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 8
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/recommended-substitutions",
            params={
                "limit": -1,
                "offset": mock_pagination_params_schema.offset,
                "count_only": mock_pagination_params_schema.count_only,
            },
        )

        # Assert
        mock_recommendations_service.get_recommended_substitutions.assert_not_called()
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    def test_get_recommended_substitutions_with_invalid_offset_parameter(
        self,
        mock_recommendations_service: Mock,
        mock_pagination_params_schema: PaginationParams,
    ) -> None:
        """Test retrieval of recommended substitutions with invalid offset parameter."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recommendations_service] = (
            lambda: mock_recommendations_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 9
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/recommended-substitutions",
            params={
                "limit": mock_pagination_params_schema.limit,
                "offset": -1,
                "count_only": mock_pagination_params_schema.count_only,
            },
        )

        # Assert
        mock_recommendations_service.get_recommended_substitutions.assert_not_called()
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    def test_get_recommended_substitutions_with_invalid_count_only_parameter(
        self,
        mock_recommendations_service: Mock,
        mock_pagination_params_schema: PaginationParams,
    ) -> None:
        """Test retrieval of recommended substitutions with invalid count_only."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recommendations_service] = (
            lambda: mock_recommendations_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        ingredient_id = 10
        response = client.get(
            f"/recipe-scraper/ingredients/{ingredient_id}/recommended-substitutions",
            params={
                "limit": mock_pagination_params_schema.limit,
                "offset": mock_pagination_params_schema.offset,
                "count_only": "invalid",
            },
        )

        # Assert
        mock_recommendations_service.get_recommended_substitutions.assert_not_called()
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    def test_get_pairing_suggestions(
        self,
        mock_recommendations_service: Mock,
        default_pagination_params_schema: PaginationParams,
    ) -> None:
        """Test retrieval of pairing suggestions."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recommendations_service] = (
            lambda: mock_recommendations_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        recipe_id = 1
        response = client.get(
            f"/recipe-scraper/recipes/{recipe_id}/pairing-suggestions",
        )

        # Assert
        mock_recommendations_service.get_pairing_suggestions.assert_called_once_with(
            recipe_id,
            default_pagination_params_schema,
            IsType(Session),
        )
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.unit
    def test_get_pairing_suggestions_with_pagination_parameters(
        self,
        mock_recommendations_service: Mock,
        mock_pagination_params_schema: PaginationParams,
    ) -> None:
        """Test retrieval of pairing suggestions with pagination parameters."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recommendations_service] = (
            lambda: mock_recommendations_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        recipe_id = 2
        response = client.get(
            f"/recipe-scraper/recipes/{recipe_id}/pairing-suggestions",
            params={
                "limit": mock_pagination_params_schema.limit,
                "offset": mock_pagination_params_schema.offset,
                "count_only": mock_pagination_params_schema.count_only,
            },
        )

        # Assert
        mock_recommendations_service.get_pairing_suggestions.assert_called_once_with(
            recipe_id,
            mock_pagination_params_schema,
            IsType(Session),
        )
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.unit
    def test_get_pairing_suggestions_with_count_only_pagination_parameters(
        self,
        mock_recommendations_service: Mock,
        mock_pagination_params_schema_count_only: PaginationParams,
    ) -> None:
        """Test retrieval of pairing suggestions with count only pagination."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recommendations_service] = (
            lambda: mock_recommendations_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        recipe_id = 2
        response = client.get(
            f"/recipe-scraper/recipes/{recipe_id}/pairing-suggestions",
            params={
                "count_only": mock_pagination_params_schema_count_only.count_only,
            },
        )

        # Assert
        mock_recommendations_service.get_pairing_suggestions.assert_called_once_with(
            recipe_id,
            mock_pagination_params_schema_count_only,
            IsType(Session),
        )
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.unit
    def test_get_pairing_suggestions_with_invalid_pagination_parameters(
        self,
        mock_recommendations_service: Mock,
        mock_pagination_params_schema_invalid_range: PaginationParams,
    ) -> None:
        """Test retrieval of pairing suggestions with invalid pagination parameters."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recommendations_service] = (
            lambda: mock_recommendations_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        recipe_id = 3
        response = client.get(
            f"/recipe-scraper/recipes/{recipe_id}/pairing-suggestions",
            params={
                "limit": mock_pagination_params_schema_invalid_range.limit,
                "offset": mock_pagination_params_schema_invalid_range.offset,
            },
        )

        # Assert
        mock_recommendations_service.get_pairing_suggestions.assert_not_called()
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.unit
    def test_get_pairing_suggestions_with_invalid_limit_parameter(
        self,
        mock_recommendations_service: Mock,
        mock_pagination_params_schema: PaginationParams,
    ) -> None:
        """Test retrieval of pairing suggestions with an invalid limit parameter."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recommendations_service] = (
            lambda: mock_recommendations_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        recipe_id = 4
        response = client.get(
            f"/recipe-scraper/recipes/{recipe_id}/pairing-suggestions",
            params={
                "limit": 0,
                "offset": mock_pagination_params_schema.offset,
                "count_only": mock_pagination_params_schema.count_only,
            },
        )

        # Assert
        mock_recommendations_service.get_pairing_suggestions.assert_not_called()
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    def test_get_pairing_suggestions_with_invalid_offset_parameter(
        self,
        mock_recommendations_service: Mock,
        mock_pagination_params_schema: PaginationParams,
    ) -> None:
        """Test retrieval of pairing suggestions with an invalid offset parameter."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recommendations_service] = (
            lambda: mock_recommendations_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        recipe_id = 5
        response = client.get(
            f"/recipe-scraper/recipes/{recipe_id}/pairing-suggestions",
            params={
                "limit": mock_pagination_params_schema.limit,
                "offset": -1,
                "count_only": mock_pagination_params_schema.count_only,
            },
        )

        # Assert
        mock_recommendations_service.get_pairing_suggestions.assert_not_called()
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    def test_get_pairing_suggestions_with_invalid_count_only_parameter(
        self,
        mock_recommendations_service: Mock,
        mock_pagination_params_schema: PaginationParams,
    ) -> None:
        """Test retrieval of pairing suggestions with an invalid count only param."""
        # Arrange
        test_app = FastAPI()
        test_app.dependency_overrides[get_recommendations_service] = (
            lambda: mock_recommendations_service
        )
        test_app.include_router(router)
        client = TestClient(test_app)

        # Act
        recipe_id = 6
        response = client.get(
            f"/recipe-scraper/recipes/{recipe_id}/pairing-suggestions",
            params={
                "limit": mock_pagination_params_schema.limit,
                "offset": mock_pagination_params_schema.offset,
                "count_only": "invalid",
            },
        )

        # Assert
        mock_recommendations_service.get_pairing_suggestions.assert_not_called()
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
