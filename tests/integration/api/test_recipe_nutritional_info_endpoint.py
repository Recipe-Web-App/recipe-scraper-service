"""Integration tests for recipe nutritional info API endpoint.

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

from app.api.dependencies import get_nutrition_service, get_recipe_management_client
from app.auth.dependencies import CurrentUser, get_current_user
from app.schemas.enums import IngredientUnit, NutrientUnit
from app.schemas.ingredient import Quantity
from app.schemas.nutrition import (
    Fats,
    IngredientNutritionalInfoResponse,
    MacroNutrients,
    NutrientValue,
    RecipeNutritionalInfoResponse,
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
def sample_nutrition_result() -> RecipeNutritionalInfoResponse:
    """Create sample nutrition result with all data."""
    return RecipeNutritionalInfoResponse(
        ingredients={
            "101": IngredientNutritionalInfoResponse(
                quantity=Quantity(amount=250.0, measurement=IngredientUnit.G),
                macro_nutrients=MacroNutrients(
                    calories=NutrientValue(
                        amount=910.0, measurement=NutrientUnit.KILOCALORIE
                    ),
                    carbs=NutrientValue(amount=190.75, measurement=NutrientUnit.GRAM),
                    protein=NutrientValue(amount=25.75, measurement=NutrientUnit.GRAM),
                    fats=Fats(
                        total=NutrientValue(amount=2.5, measurement=NutrientUnit.GRAM)
                    ),
                ),
            ),
            "102": IngredientNutritionalInfoResponse(
                quantity=Quantity(amount=100.0, measurement=IngredientUnit.G),
                macro_nutrients=MacroNutrients(
                    calories=NutrientValue(
                        amount=387.0, measurement=NutrientUnit.KILOCALORIE
                    ),
                    carbs=NutrientValue(amount=100.0, measurement=NutrientUnit.GRAM),
                    protein=NutrientValue(amount=0.0, measurement=NutrientUnit.GRAM),
                    fats=Fats(
                        total=NutrientValue(amount=0.0, measurement=NutrientUnit.GRAM)
                    ),
                ),
            ),
        },
        missing_ingredients=None,
        total=IngredientNutritionalInfoResponse(
            quantity=Quantity(amount=350.0, measurement=IngredientUnit.G),
            macro_nutrients=MacroNutrients(
                calories=NutrientValue(
                    amount=1297.0, measurement=NutrientUnit.KILOCALORIE
                ),
                carbs=NutrientValue(amount=290.75, measurement=NutrientUnit.GRAM),
                protein=NutrientValue(amount=25.75, measurement=NutrientUnit.GRAM),
                fats=Fats(
                    total=NutrientValue(amount=2.5, measurement=NutrientUnit.GRAM)
                ),
            ),
        ),
    )


@pytest.fixture
def sample_partial_nutrition_result() -> RecipeNutritionalInfoResponse:
    """Create sample nutrition result with missing ingredients."""
    return RecipeNutritionalInfoResponse(
        ingredients={
            "101": IngredientNutritionalInfoResponse(
                quantity=Quantity(amount=250.0, measurement=IngredientUnit.G),
                macro_nutrients=MacroNutrients(
                    calories=NutrientValue(
                        amount=910.0, measurement=NutrientUnit.KILOCALORIE
                    ),
                ),
            ),
        },
        missing_ingredients=[102],
        total=IngredientNutritionalInfoResponse(
            quantity=Quantity(amount=250.0, measurement=IngredientUnit.G),
            macro_nutrients=MacroNutrients(
                calories=NutrientValue(
                    amount=910.0, measurement=NutrientUnit.KILOCALORIE
                ),
            ),
        ),
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
def mock_nutrition_service(
    sample_nutrition_result: RecipeNutritionalInfoResponse,
) -> MagicMock:
    """Create mock nutrition service."""
    mock = MagicMock()
    mock.get_recipe_nutrition = AsyncMock(return_value=sample_nutrition_result)
    mock.initialize = AsyncMock()
    mock.shutdown = AsyncMock()
    return mock


@pytest.fixture
async def recipe_nutrition_client(
    app: FastAPI,
    mock_recipe_client: MagicMock,
    mock_nutrition_service: MagicMock,
) -> AsyncGenerator[AsyncClient]:
    """Create client with recipe and nutrition services mocked."""

    async def mock_get_current_user() -> CurrentUser:
        return MOCK_USER

    async def mock_get_recipe_client() -> MagicMock:
        return mock_recipe_client

    async def mock_get_nutrition() -> MagicMock:
        return mock_nutrition_service

    # Set dependency overrides
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_recipe_management_client] = mock_get_recipe_client
    app.dependency_overrides[get_nutrition_service] = mock_get_nutrition

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
        app.dependency_overrides.pop(get_nutrition_service, None)


class TestGetRecipeNutritionalInfoEndpoint:
    """Integration tests for GET /recipes/{id}/nutritional-info endpoint."""

    @pytest.mark.asyncio
    async def test_get_nutrition_success(
        self,
        recipe_nutrition_client: AsyncClient,
        mock_recipe_client: MagicMock,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should return 200 with nutrition data."""
        response = await recipe_nutrition_client.get(
            "/api/v1/recipe-scraper/recipes/123/nutritional-info"
        )

        assert response.status_code == 200

        data = response.json()
        assert "total" in data
        assert "macroNutrients" in data["total"]

        # Verify services were called
        mock_recipe_client.get_recipe.assert_called_once()
        mock_nutrition_service.get_recipe_nutrition.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_nutrition_with_include_ingredients(
        self,
        recipe_nutrition_client: AsyncClient,
    ) -> None:
        """Should include ingredients when includeIngredients=true."""
        response = await recipe_nutrition_client.get(
            "/api/v1/recipe-scraper/recipes/123/nutritional-info",
            params={"includeIngredients": "true"},
        )

        assert response.status_code == 200

        data = response.json()
        assert "total" in data
        assert "ingredients" in data
        assert len(data["ingredients"]) == 2

    @pytest.mark.asyncio
    async def test_get_nutrition_total_only(
        self,
        recipe_nutrition_client: AsyncClient,
    ) -> None:
        """Should only return total when includeIngredients=false."""
        response = await recipe_nutrition_client.get(
            "/api/v1/recipe-scraper/recipes/123/nutritional-info",
            params={"includeTotal": "true", "includeIngredients": "false"},
        )

        assert response.status_code == 200

        data = response.json()
        assert "total" in data
        assert "ingredients" not in data

    @pytest.mark.asyncio
    async def test_returns_206_with_partial_content_header(
        self,
        app: FastAPI,
        mock_recipe_client: MagicMock,
        sample_partial_nutrition_result: RecipeNutritionalInfoResponse,
    ) -> None:
        """Should return 206 with X-Partial-Content header when ingredients missing."""
        mock_partial_nutrition = MagicMock()
        mock_partial_nutrition.get_recipe_nutrition = AsyncMock(
            return_value=sample_partial_nutrition_result
        )

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_recipe_client() -> MagicMock:
            return mock_recipe_client

        async def mock_get_nutrition() -> MagicMock:
            return mock_partial_nutrition

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_recipe_management_client] = mock_get_recipe_client
        app.dependency_overrides[get_nutrition_service] = mock_get_nutrition

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/recipes/123/nutritional-info"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_recipe_management_client, None)
            app.dependency_overrides.pop(get_nutrition_service, None)

        assert response.status_code == 206
        assert "x-partial-content" in response.headers
        assert response.headers["x-partial-content"] == "102"

    @pytest.mark.asyncio
    async def test_returns_400_for_invalid_flags(
        self,
        recipe_nutrition_client: AsyncClient,
    ) -> None:
        """Should return 400 when both includeTotal and includeIngredients are false."""
        response = await recipe_nutrition_client.get(
            "/api/v1/recipe-scraper/recipes/123/nutritional-info",
            params={"includeTotal": "false", "includeIngredients": "false"},
        )

        assert response.status_code == 400

        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "BAD_REQUEST" in data["message"]

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_recipe(
        self,
        app: FastAPI,
        mock_nutrition_service: MagicMock,
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

        async def mock_get_nutrition() -> MagicMock:
            return mock_nutrition_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_recipe_management_client] = mock_get_recipe_client
        app.dependency_overrides[get_nutrition_service] = mock_get_nutrition

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/recipes/999/nutritional-info"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_recipe_management_client, None)
            app.dependency_overrides.pop(get_nutrition_service, None)

        assert response.status_code == 404

        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "NOT_FOUND" in data["message"]

    @pytest.mark.asyncio
    async def test_returns_503_for_service_unavailable(
        self,
        app: FastAPI,
        mock_nutrition_service: MagicMock,
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

        async def mock_get_nutrition() -> MagicMock:
            return mock_nutrition_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_recipe_management_client] = mock_get_recipe_client
        app.dependency_overrides[get_nutrition_service] = mock_get_nutrition

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/recipes/123/nutritional-info"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_recipe_management_client, None)
            app.dependency_overrides.pop(get_nutrition_service, None)

        assert response.status_code == 503

        data = response.json()
        assert data["error"] == "HTTP_ERROR"
        assert "SERVICE_UNAVAILABLE" in data["message"]

    @pytest.mark.asyncio
    async def test_handles_empty_recipe(
        self,
        app: FastAPI,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should handle recipe with no ingredients."""
        empty_recipe = RecipeDetailResponse(
            id=123,
            title="Empty Recipe",
            ingredients=[],
        )
        mock_client = MagicMock()
        mock_client.get_recipe = AsyncMock(return_value=empty_recipe)

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_recipe_client() -> MagicMock:
            return mock_client

        async def mock_get_nutrition() -> MagicMock:
            return mock_nutrition_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_recipe_management_client] = mock_get_recipe_client
        app.dependency_overrides[get_nutrition_service] = mock_get_nutrition

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/recipes/123/nutritional-info"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_recipe_management_client, None)
            app.dependency_overrides.pop(get_nutrition_service, None)

        assert response.status_code == 200

        data = response.json()
        assert "total" in data
        assert data["total"]["quantity"]["amount"] == 0

    @pytest.mark.asyncio
    async def test_includes_middleware_headers(
        self,
        recipe_nutrition_client: AsyncClient,
    ) -> None:
        """Should include middleware headers in response."""
        response = await recipe_nutrition_client.get(
            "/api/v1/recipe-scraper/recipes/123/nutritional-info"
        )

        assert response.status_code == 200
        assert "x-request-id" in response.headers
        assert "x-process-time" in response.headers


class TestRecipeNutritionalInfoAuthentication:
    """Tests for authentication on recipe nutritional info endpoint."""

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
                "/api/v1/recipe-scraper/recipes/123/nutritional-info"
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_403_without_permission(
        self,
        app: FastAPI,
        mock_recipe_client: MagicMock,
        mock_nutrition_service: MagicMock,
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

        async def mock_get_nutrition() -> MagicMock:
            return mock_nutrition_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_recipe_management_client] = mock_get_recipe_client
        app.dependency_overrides[get_nutrition_service] = mock_get_nutrition

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/recipes/123/nutritional-info"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_recipe_management_client, None)
            app.dependency_overrides.pop(get_nutrition_service, None)

        assert response.status_code == 403
