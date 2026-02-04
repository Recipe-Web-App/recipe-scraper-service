"""End-to-end tests for recipe pairings endpoint.

Tests cover:
- Full endpoint flow with mocked LLM
- Response structure validation
- Error scenarios
- Header verification
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_pairings_service, get_recipe_management_client
from app.auth.dependencies import CurrentUser, get_current_user
from app.llm.prompts.pairings import PairingListResult, PairingResult
from app.services.pairings.service import PairingsService
from app.services.recipe_management.exceptions import RecipeManagementNotFoundError
from app.services.recipe_management.schemas import (
    RecipeDetailResponse,
    RecipeIngredientResponse,
)


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import FastAPI


pytestmark = pytest.mark.e2e


MOCK_USER = CurrentUser(
    id="e2e-test-user",
    roles=["user"],
    permissions=["recipe:read"],
    token_type="access",
)


@pytest.fixture
def sample_llm_result() -> PairingListResult:
    """Create sample LLM pairing result."""
    return PairingListResult(
        pairings=[
            PairingResult(
                recipe_name="Garlic Bread",
                url="https://www.allrecipes.com/recipe/garlic-bread",
                pairing_reason="Classic Italian accompaniment",
                cuisine_type="Italian",
                confidence=0.95,
            ),
            PairingResult(
                recipe_name="Caesar Salad",
                url="https://www.foodnetwork.com/recipes/caesar-salad",
                pairing_reason="Light starter that balances rich pasta",
                cuisine_type="Italian",
                confidence=0.9,
            ),
            PairingResult(
                recipe_name="Tiramisu",
                url="https://www.epicurious.com/recipes/tiramisu",
                pairing_reason="Traditional Italian dessert to finish",
                cuisine_type="Italian",
                confidence=0.85,
            ),
            PairingResult(
                recipe_name="Chianti Wine",
                url="https://www.wine.com/chianti",
                pairing_reason="Classic wine pairing with Italian dishes",
                cuisine_type="Italian",
                confidence=0.88,
            ),
        ]
    )


@pytest.fixture
def sample_recipe() -> RecipeDetailResponse:
    """Create sample recipe detail."""
    return RecipeDetailResponse(
        id=456,
        title="Spaghetti Carbonara",
        description="Classic Italian pasta with eggs, cheese, and pancetta",
        ingredients=[
            RecipeIngredientResponse(
                id=1,
                ingredient_id=1,
                ingredient_name="spaghetti",
                quantity=400.0,
                unit="G",
            ),
            RecipeIngredientResponse(
                id=2,
                ingredient_id=2,
                ingredient_name="pancetta",
                quantity=200.0,
                unit="G",
            ),
            RecipeIngredientResponse(
                id=3,
                ingredient_id=3,
                ingredient_name="eggs",
                quantity=4.0,
                unit="PIECE",
            ),
            RecipeIngredientResponse(
                id=4,
                ingredient_id=4,
                ingredient_name="parmesan cheese",
                quantity=100.0,
                unit="G",
            ),
        ],
        servings=4,
    )


@pytest.fixture
def mock_llm_client(sample_llm_result: PairingListResult) -> MagicMock:
    """Create mock LLM client that returns sample data."""
    client = MagicMock()
    client.generate_structured = AsyncMock(return_value=sample_llm_result)
    client.initialize = AsyncMock()
    client.shutdown = AsyncMock()
    return client


@pytest.fixture
def mock_cache_client() -> MagicMock:
    """Create mock cache client."""
    client = MagicMock()
    client.get = AsyncMock(return_value=None)  # Cache miss
    client.setex = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_recipe_client(sample_recipe: RecipeDetailResponse) -> MagicMock:
    """Create mock recipe management client."""
    client = MagicMock()
    client.get_recipe = AsyncMock(return_value=sample_recipe)
    return client


@pytest.fixture
async def e2e_pairings_client(
    app: FastAPI,
    mock_llm_client: MagicMock,
    mock_cache_client: MagicMock,
    mock_recipe_client: MagicMock,
) -> AsyncGenerator[AsyncClient]:
    """Create e2e client with real pairings service but mocked dependencies."""
    # Create real pairings service with mocked LLM
    pairings_service = PairingsService(
        cache_client=mock_cache_client,
        llm_client=mock_llm_client,
    )
    await pairings_service.initialize()

    async def mock_get_current_user() -> CurrentUser:
        return MOCK_USER

    async def mock_get_pairings() -> PairingsService:
        return pairings_service

    async def mock_get_recipe_client() -> MagicMock:
        return mock_recipe_client

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
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_pairings_service, None)
        app.dependency_overrides.pop(get_recipe_management_client, None)
        await pairings_service.shutdown()


class TestRecipePairingsE2E:
    """E2E tests for recipe pairings endpoint."""

    async def test_returns_pairings_for_valid_recipe(
        self,
        e2e_pairings_client: AsyncClient,
    ) -> None:
        """Should return pairing suggestions for a valid recipe."""
        response = await e2e_pairings_client.get(
            "/api/v1/recipe-scraper/recipes/456/pairings"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["recipeId"] == 456
        assert len(data["pairingSuggestions"]) == 4
        assert data["count"] == 4

    async def test_pagination_parameters_work(
        self,
        e2e_pairings_client: AsyncClient,
    ) -> None:
        """Should handle pagination parameters correctly."""
        response = await e2e_pairings_client.get(
            "/api/v1/recipe-scraper/recipes/456/pairings?limit=2&offset=1"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 2
        assert data["offset"] == 1
        assert len(data["pairingSuggestions"]) == 2
        assert data["count"] == 4  # Total count unchanged

    async def test_count_only_returns_metadata(
        self,
        e2e_pairings_client: AsyncClient,
    ) -> None:
        """Should return only count when countOnly=true."""
        response = await e2e_pairings_client.get(
            "/api/v1/recipe-scraper/recipes/456/pairings?countOnly=true"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pairingSuggestions"] == []
        assert data["count"] == 4


class TestPairingResponseValidationE2E:
    """E2E tests for response structure validation."""

    async def test_response_has_required_fields(
        self,
        e2e_pairings_client: AsyncClient,
    ) -> None:
        """Should include all required fields in response."""
        response = await e2e_pairings_client.get(
            "/api/v1/recipe-scraper/recipes/456/pairings"
        )

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "recipeId" in data
        assert "pairingSuggestions" in data
        assert "limit" in data
        assert "offset" in data
        assert "count" in data

    async def test_pairing_suggestions_have_correct_structure(
        self,
        e2e_pairings_client: AsyncClient,
    ) -> None:
        """Should have correct structure for each pairing suggestion."""
        response = await e2e_pairings_client.get(
            "/api/v1/recipe-scraper/recipes/456/pairings"
        )

        assert response.status_code == 200
        data = response.json()

        for suggestion in data["pairingSuggestions"]:
            assert "recipeName" in suggestion
            assert "url" in suggestion
            assert suggestion["recipeName"]  # Not empty
            assert suggestion["url"].startswith("http")

    async def test_urls_are_valid_format(
        self,
        e2e_pairings_client: AsyncClient,
    ) -> None:
        """Should return valid URL format for each pairing."""
        response = await e2e_pairings_client.get(
            "/api/v1/recipe-scraper/recipes/456/pairings"
        )

        assert response.status_code == 200
        data = response.json()

        for suggestion in data["pairingSuggestions"]:
            url = suggestion["url"]
            assert url.startswith(("http://", "https://"))

    async def test_recipe_names_are_not_empty(
        self,
        e2e_pairings_client: AsyncClient,
    ) -> None:
        """Should return non-empty recipe names."""
        response = await e2e_pairings_client.get(
            "/api/v1/recipe-scraper/recipes/456/pairings"
        )

        assert response.status_code == 200
        data = response.json()

        for suggestion in data["pairingSuggestions"]:
            assert len(suggestion["recipeName"]) > 0


class TestPairingErrorHandlingE2E:
    """E2E tests for error handling scenarios."""

    async def test_returns_404_when_recipe_not_found(
        self,
        app: FastAPI,
        mock_llm_client: MagicMock,
        mock_cache_client: MagicMock,
    ) -> None:
        """Should return 404 when recipe doesn't exist."""
        # Create mock that raises not found
        recipe_client = MagicMock()
        recipe_client.get_recipe = AsyncMock(
            side_effect=RecipeManagementNotFoundError("Not found")
        )

        pairings_service = PairingsService(
            cache_client=mock_cache_client,
            llm_client=mock_llm_client,
        )
        await pairings_service.initialize()

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_pairings() -> PairingsService:
            return pairings_service

        async def mock_get_recipe_client() -> MagicMock:
            return recipe_client

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_pairings_service] = mock_get_pairings
        app.dependency_overrides[get_recipe_management_client] = mock_get_recipe_client

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/recipes/999/pairings"
                )

            assert response.status_code == 404
        finally:
            # Clean up
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_pairings_service, None)
            app.dependency_overrides.pop(get_recipe_management_client, None)
            await pairings_service.shutdown()

    async def test_invalid_limit_returns_422(
        self,
        e2e_pairings_client: AsyncClient,
    ) -> None:
        """Should return 422 for invalid limit parameter."""
        response = await e2e_pairings_client.get(
            "/api/v1/recipe-scraper/recipes/456/pairings?limit=0"
        )

        assert response.status_code == 422

    async def test_negative_offset_returns_422(
        self,
        e2e_pairings_client: AsyncClient,
    ) -> None:
        """Should return 422 for negative offset."""
        response = await e2e_pairings_client.get(
            "/api/v1/recipe-scraper/recipes/456/pairings?offset=-1"
        )

        assert response.status_code == 422


class TestPairingHeadersE2E:
    """E2E tests for response headers."""

    async def test_response_includes_request_id(
        self,
        e2e_pairings_client: AsyncClient,
    ) -> None:
        """Should include x-request-id header."""
        response = await e2e_pairings_client.get(
            "/api/v1/recipe-scraper/recipes/456/pairings"
        )

        assert response.status_code == 200
        assert "x-request-id" in response.headers

    async def test_response_includes_process_time(
        self,
        e2e_pairings_client: AsyncClient,
    ) -> None:
        """Should include x-process-time header."""
        response = await e2e_pairings_client.get(
            "/api/v1/recipe-scraper/recipes/456/pairings"
        )

        assert response.status_code == 200
        assert "x-process-time" in response.headers

    async def test_content_type_is_json(
        self,
        e2e_pairings_client: AsyncClient,
    ) -> None:
        """Should return application/json content type."""
        response = await e2e_pairings_client.get(
            "/api/v1/recipe-scraper/recipes/456/pairings"
        )

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
