"""Integration tests for recipe shopping info API endpoint.

Tests cover:
- Full endpoint flow with mocked services
- Authentication and authorization
- Error handling with real middleware stack
- 206 Partial Content response handling
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_recipe_management_client, get_shopping_service
from app.auth.dependencies import CurrentUser, get_current_user
from app.schemas.enums import IngredientUnit
from app.schemas.ingredient import Quantity
from app.schemas.shopping import (
    IngredientShoppingInfoResponse,
    RecipeShoppingInfoResponse,
)
from app.services.recipe_management.exceptions import (
    RecipeManagementNotFoundError,
    RecipeManagementUnavailableError,
)
from app.services.recipe_management.schemas import (
    IngredientUnit as RecipeIngredientUnit,
)
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
)


@pytest.fixture
def sample_recipe_response() -> RecipeDetailResponse:
    """Create sample recipe response with ingredients."""
    return RecipeDetailResponse(
        id=123,
        title="Test Recipe",
        slug="test-recipe",
        description="A test recipe",
        servings=4.0,
        ingredients=[
            RecipeIngredientResponse(
                id=1,
                ingredient_id=101,
                ingredient_name="flour",
                quantity=250.0,
                unit=RecipeIngredientUnit.G,
            ),
            RecipeIngredientResponse(
                id=2,
                ingredient_id=102,
                ingredient_name="sugar",
                quantity=100.0,
                unit=RecipeIngredientUnit.G,
            ),
        ],
    )


@pytest.fixture
def sample_shopping_result() -> RecipeShoppingInfoResponse:
    """Create sample shopping result with all data."""
    return RecipeShoppingInfoResponse(
        recipe_id=123,
        ingredients={
            "flour": IngredientShoppingInfoResponse(
                ingredient_name="flour",
                quantity=Quantity(amount=250.0, measurement=IngredientUnit.G),
                estimated_price="0.45",
                price_confidence=0.85,
                data_source="USDA_FVP",
                currency="USD",
            ),
            "sugar": IngredientShoppingInfoResponse(
                ingredient_name="sugar",
                quantity=Quantity(amount=100.0, measurement=IngredientUnit.G),
                estimated_price="0.25",
                price_confidence=0.90,
                data_source="USDA_FVP",
                currency="USD",
            ),
        },
        total_estimated_cost="0.70",
        missing_ingredients=None,
    )


@pytest.fixture
def sample_partial_shopping_result() -> RecipeShoppingInfoResponse:
    """Create sample shopping result with missing ingredients."""
    return RecipeShoppingInfoResponse(
        recipe_id=123,
        ingredients={
            "flour": IngredientShoppingInfoResponse(
                ingredient_name="flour",
                quantity=Quantity(amount=250.0, measurement=IngredientUnit.G),
                estimated_price="0.45",
                price_confidence=0.85,
                data_source="USDA_FVP",
                currency="USD",
            ),
        },
        total_estimated_cost="0.45",
        missing_ingredients=[102],
    )


@pytest.fixture
def mock_recipe_client(sample_recipe_response: RecipeDetailResponse) -> MagicMock:
    """Create mock recipe client."""
    mock = MagicMock()
    mock.get_recipe = AsyncMock(return_value=sample_recipe_response)
    mock.initialize = AsyncMock()
    mock.shutdown = AsyncMock()
    return mock


@pytest.fixture
def mock_shopping_service(
    sample_shopping_result: RecipeShoppingInfoResponse,
) -> MagicMock:
    """Create mock shopping service."""
    mock = MagicMock()
    mock.get_recipe_shopping_info = AsyncMock(return_value=sample_shopping_result)
    mock.initialize = AsyncMock()
    mock.shutdown = AsyncMock()
    return mock


@pytest.fixture
async def recipe_shopping_client(
    app: FastAPI,
    mock_recipe_client: MagicMock,
    mock_shopping_service: MagicMock,
) -> AsyncGenerator[AsyncClient]:
    """Create client with recipe and shopping services mocked."""

    async def mock_get_current_user() -> CurrentUser:
        return MOCK_USER

    async def mock_get_recipe_client() -> MagicMock:
        return mock_recipe_client

    async def mock_get_shopping() -> MagicMock:
        return mock_shopping_service

    # Set dependency overrides
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_recipe_management_client] = mock_get_recipe_client
    app.dependency_overrides[get_shopping_service] = mock_get_shopping

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_recipe_management_client, None)
        app.dependency_overrides.pop(get_shopping_service, None)


class TestGetRecipeShoppingInfoEndpoint:
    """Integration tests for GET /recipes/{id}/shopping-info endpoint."""

    @pytest.mark.asyncio
    async def test_get_shopping_info_success(
        self,
        recipe_shopping_client: AsyncClient,
        mock_recipe_client: MagicMock,
        mock_shopping_service: MagicMock,
    ) -> None:
        """Should return 200 with shopping data."""
        response = await recipe_shopping_client.get(
            "/api/v1/recipe-scraper/recipes/123/shopping-info"
        )

        assert response.status_code == 200

        data = response.json()
        assert "recipeId" in data
        assert data["recipeId"] == 123
        assert "ingredients" in data
        assert "totalEstimatedCost" in data
        assert data["totalEstimatedCost"] == "0.70"

        # Verify services were called
        mock_recipe_client.get_recipe.assert_called_once()
        mock_shopping_service.get_recipe_shopping_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_206_with_partial_content_header(
        self,
        app: FastAPI,
        mock_recipe_client: MagicMock,
        sample_partial_shopping_result: RecipeShoppingInfoResponse,
    ) -> None:
        """Should return 206 with X-Partial-Content header when ingredients missing."""
        mock_partial_shopping = MagicMock()
        mock_partial_shopping.get_recipe_shopping_info = AsyncMock(
            return_value=sample_partial_shopping_result
        )

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_recipe_client() -> MagicMock:
            return mock_recipe_client

        async def mock_get_shopping() -> MagicMock:
            return mock_partial_shopping

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_recipe_management_client] = mock_get_recipe_client
        app.dependency_overrides[get_shopping_service] = mock_get_shopping

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/recipes/123/shopping-info"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_recipe_management_client, None)
            app.dependency_overrides.pop(get_shopping_service, None)

        assert response.status_code == 206
        assert "x-partial-content" in response.headers
        assert response.headers["x-partial-content"] == "102"

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_recipe(
        self,
        app: FastAPI,
        mock_shopping_service: MagicMock,
    ) -> None:
        """Should return 404 when recipe not found."""
        mock_client = MagicMock()
        mock_client.get_recipe = AsyncMock(
            side_effect=RecipeManagementNotFoundError("Recipe not found")
        )

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_recipe_client() -> MagicMock:
            return mock_client

        async def mock_get_shopping() -> MagicMock:
            return mock_shopping_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_recipe_management_client] = mock_get_recipe_client
        app.dependency_overrides[get_shopping_service] = mock_get_shopping

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/recipes/999/shopping-info"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_recipe_management_client, None)
            app.dependency_overrides.pop(get_shopping_service, None)

        assert response.status_code == 404

        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "NOT_FOUND" in data["message"]

    @pytest.mark.asyncio
    async def test_returns_503_for_service_unavailable(
        self,
        app: FastAPI,
        mock_shopping_service: MagicMock,
    ) -> None:
        """Should return 503 when Recipe Management Service unavailable."""
        mock_client = MagicMock()
        mock_client.get_recipe = AsyncMock(
            side_effect=RecipeManagementUnavailableError("Service unavailable")
        )

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_recipe_client() -> MagicMock:
            return mock_client

        async def mock_get_shopping() -> MagicMock:
            return mock_shopping_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_recipe_management_client] = mock_get_recipe_client
        app.dependency_overrides[get_shopping_service] = mock_get_shopping

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/recipes/123/shopping-info"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_recipe_management_client, None)
            app.dependency_overrides.pop(get_shopping_service, None)

        assert response.status_code == 503

        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "SERVICE_UNAVAILABLE" in data["message"]

    @pytest.mark.asyncio
    async def test_handles_empty_recipe(
        self,
        app: FastAPI,
        mock_shopping_service: MagicMock,
    ) -> None:
        """Should handle recipe with no ingredients."""
        empty_recipe = RecipeDetailResponse(
            id=123,
            title="Empty Recipe",
            ingredients=[],
        )
        mock_client = MagicMock()
        mock_client.get_recipe = AsyncMock(return_value=empty_recipe)

        # Mock returns empty shopping result for empty recipe
        empty_shopping = RecipeShoppingInfoResponse(
            recipe_id=123,
            ingredients={},
            total_estimated_cost="0.00",
            missing_ingredients=None,
        )
        mock_empty_shopping = MagicMock()
        mock_empty_shopping.get_recipe_shopping_info = AsyncMock(
            return_value=empty_shopping
        )

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_recipe_client() -> MagicMock:
            return mock_client

        async def mock_get_shopping() -> MagicMock:
            return mock_empty_shopping

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_recipe_management_client] = mock_get_recipe_client
        app.dependency_overrides[get_shopping_service] = mock_get_shopping

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/recipes/123/shopping-info"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_recipe_management_client, None)
            app.dependency_overrides.pop(get_shopping_service, None)

        assert response.status_code == 200

        data = response.json()
        assert data["ingredients"] == {}
        assert data["totalEstimatedCost"] == "0.00"

    @pytest.mark.asyncio
    async def test_includes_middleware_headers(
        self,
        recipe_shopping_client: AsyncClient,
    ) -> None:
        """Should include middleware headers in response."""
        response = await recipe_shopping_client.get(
            "/api/v1/recipe-scraper/recipes/123/shopping-info"
        )

        assert response.status_code == 200
        assert "x-request-id" in response.headers
        assert "x-process-time" in response.headers


class TestRecipeShoppingInfoAuthentication:
    """Tests for authentication on recipe shopping info endpoint."""

    @pytest.mark.asyncio
    async def test_returns_401_without_auth(
        self,
        app: FastAPI,
    ) -> None:
        """Should return 401 when not authenticated."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/v1/recipe-scraper/recipes/123/shopping-info"
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_403_without_permission(
        self,
        app: FastAPI,
        mock_recipe_client: MagicMock,
        mock_shopping_service: MagicMock,
    ) -> None:
        """Should return 403 when user lacks required permission."""
        user_without_permission = CurrentUser(
            id="test-user-no-perms",
            roles=[],
            permissions=[],
        )

        async def mock_get_current_user() -> CurrentUser:
            return user_without_permission

        async def mock_get_recipe_client() -> MagicMock:
            return mock_recipe_client

        async def mock_get_shopping() -> MagicMock:
            return mock_shopping_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_recipe_management_client] = mock_get_recipe_client
        app.dependency_overrides[get_shopping_service] = mock_get_shopping

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/recipes/123/shopping-info"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_recipe_management_client, None)
            app.dependency_overrides.pop(get_shopping_service, None)

        assert response.status_code == 403
