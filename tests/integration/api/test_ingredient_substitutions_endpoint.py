"""Integration tests for ingredient substitutions API endpoint.

Tests cover:
- Full endpoint flow with mocked services
- Authentication and authorization
- Error handling with real middleware stack
- Query parameter validation
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_substitution_service
from app.auth.dependencies import CurrentUser, get_current_user
from app.schemas.enums import IngredientUnit
from app.schemas.ingredient import Ingredient
from app.schemas.recommendations import (
    ConversionRatio,
    IngredientSubstitution,
    RecommendedSubstitutionsResponse,
)
from app.services.substitution.exceptions import LLMGenerationError


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import FastAPI


pytestmark = pytest.mark.integration


# Mock user for authenticated tests
MOCK_USER = CurrentUser(
    id="test-user-123",
    roles=["user"],
    permissions=["recipe:read"],
    token_type="access",
)


@pytest.fixture
def sample_substitution_result() -> RecommendedSubstitutionsResponse:
    """Create sample substitution result with all data."""
    return RecommendedSubstitutionsResponse(
        ingredient=Ingredient(
            ingredient_id=None,
            name="butter",
            quantity=None,
        ),
        recommended_substitutions=[
            IngredientSubstitution(
                ingredient="coconut oil",
                quantity=None,
                conversion_ratio=ConversionRatio(
                    ratio=1.0,
                    measurement=IngredientUnit.CUP,
                ),
            ),
            IngredientSubstitution(
                ingredient="olive oil",
                quantity=None,
                conversion_ratio=ConversionRatio(
                    ratio=0.75,
                    measurement=IngredientUnit.CUP,
                ),
            ),
            IngredientSubstitution(
                ingredient="applesauce",
                quantity=None,
                conversion_ratio=ConversionRatio(
                    ratio=0.5,
                    measurement=IngredientUnit.CUP,
                ),
            ),
        ],
        limit=50,
        offset=0,
        count=3,
    )


@pytest.fixture
def mock_substitution_service(
    sample_substitution_result: RecommendedSubstitutionsResponse,
) -> MagicMock:
    """Create mock substitution service."""
    mock = MagicMock()
    mock.get_substitutions = AsyncMock(return_value=sample_substitution_result)
    mock.initialize = AsyncMock()
    mock.shutdown = AsyncMock()
    return mock


@pytest.fixture
async def substitution_client(
    app: FastAPI,
    mock_substitution_service: MagicMock,
) -> AsyncGenerator[AsyncClient]:
    """Create client with substitution service mocked."""

    async def mock_get_current_user() -> CurrentUser:
        return MOCK_USER

    async def mock_get_substitution() -> MagicMock:
        return mock_substitution_service

    # Set dependency overrides
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_substitution_service] = mock_get_substitution

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_substitution_service, None)


class TestGetIngredientSubstitutionsEndpoint:
    """Integration tests for GET /ingredients/{id}/substitutions endpoint."""

    async def test_returns_200_with_valid_ingredient(
        self,
        substitution_client: AsyncClient,
        mock_substitution_service: MagicMock,
    ) -> None:
        """Should return 200 with substitution data."""
        response = await substitution_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ingredient"]["name"] == "butter"
        assert len(data["recommendedSubstitutions"]) == 3
        assert data["limit"] == 50
        assert data["offset"] == 0
        assert data["count"] == 3

    async def test_accepts_pagination_parameters(
        self,
        substitution_client: AsyncClient,
        mock_substitution_service: MagicMock,
    ) -> None:
        """Should accept limit and offset parameters."""
        response = await substitution_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions?limit=10&offset=5"
        )

        assert response.status_code == 200
        call_kwargs = mock_substitution_service.get_substitutions.call_args[1]
        assert call_kwargs["limit"] == 10
        assert call_kwargs["offset"] == 5

    async def test_accepts_quantity_parameters(
        self,
        substitution_client: AsyncClient,
        mock_substitution_service: MagicMock,
    ) -> None:
        """Should accept amount and measurement parameters."""
        response = await substitution_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions"
            "?amount=1&measurement=CUP"
        )

        assert response.status_code == 200
        call_kwargs = mock_substitution_service.get_substitutions.call_args[1]
        assert call_kwargs["quantity"] is not None
        assert call_kwargs["quantity"].amount == 1.0
        assert call_kwargs["quantity"].measurement == IngredientUnit.CUP

    async def test_returns_400_with_only_amount(
        self,
        substitution_client: AsyncClient,
    ) -> None:
        """Should return 400 when only amount is provided."""
        response = await substitution_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions?amount=1"
        )

        assert response.status_code == 400
        data = response.json()
        # Middleware wraps errors with HTTP_ERROR and includes original error in message
        assert data["error"] == "HTTP_ERROR"
        assert "INVALID_QUANTITY_PARAMS" in data["message"]

    async def test_returns_400_with_only_measurement(
        self,
        substitution_client: AsyncClient,
    ) -> None:
        """Should return 400 when only measurement is provided."""
        response = await substitution_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions?measurement=CUP"
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "INVALID_QUANTITY_PARAMS" in data["message"]

    async def test_returns_404_when_not_found(
        self,
        substitution_client: AsyncClient,
        mock_substitution_service: MagicMock,
    ) -> None:
        """Should return 404 when service returns None."""
        mock_substitution_service.get_substitutions = AsyncMock(return_value=None)

        response = await substitution_client.get(
            "/api/v1/recipe-scraper/ingredients/unknown/substitutions"
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "INGREDIENT_NOT_FOUND" in data["message"]

    async def test_returns_503_when_llm_unavailable(
        self,
        substitution_client: AsyncClient,
        mock_substitution_service: MagicMock,
    ) -> None:
        """Should return 503 when LLM generation fails."""
        mock_substitution_service.get_substitutions = AsyncMock(
            side_effect=LLMGenerationError(
                message="LLM unavailable",
                ingredient="butter",
            )
        )

        response = await substitution_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions"
        )

        assert response.status_code == 503
        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "LLM_UNAVAILABLE" in data["message"]

    async def test_count_only_returns_empty_list(
        self,
        substitution_client: AsyncClient,
        mock_substitution_service: MagicMock,
    ) -> None:
        """Should return empty list when countOnly=true."""
        response = await substitution_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions?countOnly=true"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["recommendedSubstitutions"] == []
        assert data["count"] == 3


class TestPaginationValidation:
    """Integration tests for pagination parameter validation."""

    async def test_rejects_limit_zero(
        self,
        substitution_client: AsyncClient,
    ) -> None:
        """Should reject limit=0."""
        response = await substitution_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions?limit=0"
        )

        assert response.status_code == 422

    async def test_rejects_limit_over_100(
        self,
        substitution_client: AsyncClient,
    ) -> None:
        """Should reject limit > 100."""
        response = await substitution_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions?limit=101"
        )

        assert response.status_code == 422

    async def test_rejects_negative_offset(
        self,
        substitution_client: AsyncClient,
    ) -> None:
        """Should reject negative offset."""
        response = await substitution_client.get(
            "/api/v1/recipe-scraper/ingredients/butter/substitutions?offset=-1"
        )

        assert response.status_code == 422


class TestAuthentication:
    """Integration tests for authentication requirements."""

    async def test_returns_401_without_auth(
        self,
        app: FastAPI,
    ) -> None:
        """Should return 401 when not authenticated."""
        # Remove auth overrides
        app.dependency_overrides.pop(get_current_user, None)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/v1/recipe-scraper/ingredients/butter/substitutions"
            )

        assert response.status_code == 401
