"""Integration tests for recipe pairings API endpoint.

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

from app.api.dependencies import get_pairings_service, get_recipe_management_client
from app.auth.dependencies import CurrentUser, get_current_user
from app.schemas.ingredient import WebRecipe
from app.schemas.recommendations import PairingSuggestionsResponse
from app.services.pairings.exceptions import LLMGenerationError
from app.services.pairings.service import RecipeContext
from app.services.recipe_management.exceptions import RecipeManagementNotFoundError
from app.services.recipe_management.schemas import (
    RecipeDetailResponse,
    RecipeIngredientResponse,
)


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
def sample_pairing_result() -> PairingSuggestionsResponse:
    """Create sample pairing result with all data."""
    return PairingSuggestionsResponse(
        recipe_id=123,
        pairing_suggestions=[
            WebRecipe(
                recipe_name="Roasted Asparagus with Parmesan",
                url="https://www.allrecipes.com/recipe/123/roasted-asparagus/",
            ),
            WebRecipe(
                recipe_name="Lemon Rice Pilaf",
                url="https://www.foodnetwork.com/recipes/lemon-rice-pilaf",
            ),
            WebRecipe(
                recipe_name="Caesar Salad",
                url="https://www.epicurious.com/recipes/caesar-salad",
            ),
        ],
        limit=50,
        offset=0,
        count=3,
    )


@pytest.fixture
def sample_recipe_detail() -> RecipeDetailResponse:
    """Create sample recipe detail response."""
    return RecipeDetailResponse(
        id=123,
        title="Grilled Salmon with Lemon",
        description="A delicious grilled salmon recipe",
        ingredients=[
            RecipeIngredientResponse(
                id=1,
                ingredient_id=1,
                ingredient_name="salmon fillet",
                quantity=2.0,
                unit="PIECE",
            ),
            RecipeIngredientResponse(
                id=2,
                ingredient_id=2,
                ingredient_name="lemon",
                quantity=1.0,
                unit="PIECE",
            ),
        ],
        servings=4,
    )


@pytest.fixture
def mock_pairings_service(
    sample_pairing_result: PairingSuggestionsResponse,
) -> MagicMock:
    """Create mock pairings service."""
    mock = MagicMock()
    mock.get_pairings = AsyncMock(return_value=sample_pairing_result)
    mock.initialize = AsyncMock()
    mock.shutdown = AsyncMock()
    return mock


@pytest.fixture
def mock_recipe_client(
    sample_recipe_detail: RecipeDetailResponse,
) -> MagicMock:
    """Create mock recipe management client."""
    mock = MagicMock()
    mock.get_recipe = AsyncMock(return_value=sample_recipe_detail)
    return mock


@pytest.fixture
async def pairings_client(
    app: FastAPI,
    mock_pairings_service: MagicMock,
    mock_recipe_client: MagicMock,
) -> AsyncGenerator[AsyncClient]:
    """Create client with pairings service mocked."""

    async def mock_get_current_user() -> CurrentUser:
        return MOCK_USER

    async def mock_get_pairings() -> MagicMock:
        return mock_pairings_service

    async def mock_get_recipe_client() -> MagicMock:
        return mock_recipe_client

    # Set dependency overrides
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_pairings_service] = mock_get_pairings
    app.dependency_overrides[get_recipe_management_client] = mock_get_recipe_client

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_pairings_service, None)
        app.dependency_overrides.pop(get_recipe_management_client, None)


class TestGetRecipePairingsEndpoint:
    """Integration tests for GET /recipes/{recipeId}/pairings endpoint."""

    async def test_returns_200_with_valid_recipe(
        self,
        pairings_client: AsyncClient,
        mock_pairings_service: MagicMock,
    ) -> None:
        """Should return 200 with pairing data."""
        response = await pairings_client.get(
            "/api/v1/recipe-scraper/recipes/123/pairings"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["recipeId"] == 123
        assert len(data["pairingSuggestions"]) == 3
        assert data["limit"] == 50
        assert data["offset"] == 0
        assert data["count"] == 3

    async def test_accepts_pagination_parameters(
        self,
        pairings_client: AsyncClient,
        mock_pairings_service: MagicMock,
    ) -> None:
        """Should accept limit and offset parameters."""
        response = await pairings_client.get(
            "/api/v1/recipe-scraper/recipes/123/pairings?limit=10&offset=5"
        )

        assert response.status_code == 200
        call_kwargs = mock_pairings_service.get_pairings.call_args[1]
        assert call_kwargs["limit"] == 10
        assert call_kwargs["offset"] == 5

    async def test_count_only_returns_empty_list(
        self,
        pairings_client: AsyncClient,
        mock_pairings_service: MagicMock,
    ) -> None:
        """Should return empty list when countOnly=true."""
        response = await pairings_client.get(
            "/api/v1/recipe-scraper/recipes/123/pairings?countOnly=true"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pairingSuggestions"] == []
        assert data["count"] == 3

    async def test_returns_404_when_recipe_not_found(
        self,
        pairings_client: AsyncClient,
        mock_recipe_client: MagicMock,
    ) -> None:
        """Should return 404 when recipe doesn't exist."""
        mock_recipe_client.get_recipe = AsyncMock(
            side_effect=RecipeManagementNotFoundError("Not found")
        )

        response = await pairings_client.get(
            "/api/v1/recipe-scraper/recipes/999/pairings"
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "NOT_FOUND" in data["message"]

    async def test_returns_503_when_llm_unavailable(
        self,
        pairings_client: AsyncClient,
        mock_pairings_service: MagicMock,
    ) -> None:
        """Should return 503 when LLM generation fails."""
        mock_pairings_service.get_pairings = AsyncMock(
            side_effect=LLMGenerationError(
                message="LLM unavailable",
                recipe_id=123,
            )
        )

        response = await pairings_client.get(
            "/api/v1/recipe-scraper/recipes/123/pairings"
        )

        assert response.status_code == 503
        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "LLM_UNAVAILABLE" in data["message"]

    async def test_passes_recipe_context_to_service(
        self,
        pairings_client: AsyncClient,
        mock_pairings_service: MagicMock,
        sample_recipe_detail: RecipeDetailResponse,
    ) -> None:
        """Should pass correct recipe context to service."""
        response = await pairings_client.get(
            "/api/v1/recipe-scraper/recipes/123/pairings"
        )

        assert response.status_code == 200

        # Verify context was built correctly
        call_args = mock_pairings_service.get_pairings.call_args
        context = call_args[1]["context"]
        assert isinstance(context, RecipeContext)
        assert context.recipe_id == 123
        assert context.title == sample_recipe_detail.title
        assert len(context.ingredients) == 2


class TestPaginationValidation:
    """Integration tests for pagination parameter validation."""

    async def test_rejects_limit_zero(
        self,
        pairings_client: AsyncClient,
    ) -> None:
        """Should reject limit=0."""
        response = await pairings_client.get(
            "/api/v1/recipe-scraper/recipes/123/pairings?limit=0"
        )

        assert response.status_code == 422

    async def test_rejects_limit_over_100(
        self,
        pairings_client: AsyncClient,
    ) -> None:
        """Should reject limit > 100."""
        response = await pairings_client.get(
            "/api/v1/recipe-scraper/recipes/123/pairings?limit=101"
        )

        assert response.status_code == 422

    async def test_rejects_negative_offset(
        self,
        pairings_client: AsyncClient,
    ) -> None:
        """Should reject negative offset."""
        response = await pairings_client.get(
            "/api/v1/recipe-scraper/recipes/123/pairings?offset=-1"
        )

        assert response.status_code == 422

    async def test_rejects_invalid_recipe_id(
        self,
        pairings_client: AsyncClient,
    ) -> None:
        """Should reject recipe ID < 1."""
        response = await pairings_client.get(
            "/api/v1/recipe-scraper/recipes/0/pairings"
        )

        assert response.status_code == 422


class TestAuthentication:
    """Integration tests for authentication requirements."""

    async def test_returns_401_without_auth(
        self,
        app: FastAPI,
        mock_pairings_service: MagicMock,
        mock_recipe_client: MagicMock,
    ) -> None:
        """Should return 401 when not authenticated."""
        # Remove auth overrides
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides[get_pairings_service] = lambda: mock_pairings_service
        app.dependency_overrides[get_recipe_management_client] = (
            lambda: mock_recipe_client
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/recipe-scraper/recipes/123/pairings")

        assert response.status_code == 401

        # Clean up
        app.dependency_overrides.pop(get_pairings_service, None)
        app.dependency_overrides.pop(get_recipe_management_client, None)


class TestResponseFormat:
    """Integration tests for response format."""

    async def test_response_uses_camel_case(
        self,
        pairings_client: AsyncClient,
    ) -> None:
        """Should return response with camelCase field names."""
        response = await pairings_client.get(
            "/api/v1/recipe-scraper/recipes/123/pairings"
        )

        assert response.status_code == 200
        data = response.json()

        # Check camelCase fields
        assert "recipeId" in data
        assert "pairingSuggestions" in data
        assert "recipeName" in data["pairingSuggestions"][0]

    async def test_response_includes_required_headers(
        self,
        pairings_client: AsyncClient,
    ) -> None:
        """Should include required response headers."""
        response = await pairings_client.get(
            "/api/v1/recipe-scraper/recipes/123/pairings"
        )

        assert response.status_code == 200
        assert "x-request-id" in response.headers
        assert "x-process-time" in response.headers
