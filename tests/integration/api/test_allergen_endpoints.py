"""Integration tests for allergen API endpoints.

Tests cover:
- GET /ingredients/{id}/allergens endpoint flow
- GET /recipes/{recipeId}/allergens endpoint flow
- Authentication and authorization
- Error handling (404, 503)
- Query parameter validation
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_allergen_service, get_recipe_management_client
from app.auth.dependencies import CurrentUser, get_current_user
from app.schemas.allergen import (
    AllergenDataSource,
    AllergenInfo,
    AllergenPresenceType,
    IngredientAllergenResponse,
    RecipeAllergenResponse,
)
from app.schemas.enums import Allergen
from app.services.recipe_management.exceptions import (
    RecipeManagementNotFoundError,
    RecipeManagementUnavailableError,
)


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import FastAPI


pytestmark = pytest.mark.integration


# Mock user with recipe:read permission
MOCK_USER = CurrentUser(
    id="test-user-123",
    roles=["user"],
    permissions=["recipe:read"],
)


@pytest.fixture
def sample_ingredient_allergen_response() -> IngredientAllergenResponse:
    """Create sample allergen response for flour."""
    return IngredientAllergenResponse(
        ingredient_id=1,
        ingredient_name="flour",
        usda_food_description="Wheat flour, white, all-purpose",
        allergens=[
            AllergenInfo(
                allergen=Allergen.GLUTEN,
                presence_type=AllergenPresenceType.CONTAINS,
                confidence_score=1.0,
                source_notes="Contains wheat gluten",
            ),
            AllergenInfo(
                allergen=Allergen.WHEAT,
                presence_type=AllergenPresenceType.CONTAINS,
                confidence_score=1.0,
                source_notes="Made from wheat",
            ),
        ],
        data_source=AllergenDataSource.USDA,
        overall_confidence=1.0,
    )


@pytest.fixture
def sample_recipe_allergen_response() -> RecipeAllergenResponse:
    """Create sample recipe allergen response."""
    return RecipeAllergenResponse(
        contains=[Allergen.GLUTEN, Allergen.MILK],
        may_contain=[Allergen.TREE_NUTS],
        allergens=[
            AllergenInfo(
                allergen=Allergen.GLUTEN,
                presence_type=AllergenPresenceType.CONTAINS,
            ),
            AllergenInfo(
                allergen=Allergen.MILK,
                presence_type=AllergenPresenceType.CONTAINS,
            ),
            AllergenInfo(
                allergen=Allergen.TREE_NUTS,
                presence_type=AllergenPresenceType.MAY_CONTAIN,
            ),
        ],
        missing_ingredients=[],
    )


@pytest.fixture
def mock_allergen_service(
    sample_ingredient_allergen_response: IngredientAllergenResponse,
) -> MagicMock:
    """Create mock allergen service."""
    mock = MagicMock()
    mock.get_ingredient_allergens = AsyncMock(
        return_value=sample_ingredient_allergen_response
    )
    mock.get_recipe_allergens = AsyncMock()
    mock.initialize = AsyncMock()
    mock.shutdown = AsyncMock()
    return mock


@pytest.fixture
async def ingredient_allergen_client(
    app: FastAPI,
    mock_allergen_service: MagicMock,
) -> AsyncGenerator[AsyncClient]:
    """Create client with allergen service mocked."""

    async def mock_get_current_user() -> CurrentUser:
        return MOCK_USER

    async def mock_get_allergen() -> MagicMock:
        return mock_allergen_service

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_allergen_service] = mock_get_allergen

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_allergen_service, None)


class TestGetIngredientAllergensEndpoint:
    """Integration tests for GET /ingredients/{id}/allergens endpoint."""

    async def test_returns_200_with_allergen_data(
        self,
        ingredient_allergen_client: AsyncClient,
        mock_allergen_service: MagicMock,
    ) -> None:
        """Should return 200 with allergen data for known ingredient."""
        response = await ingredient_allergen_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/allergens"
        )

        assert response.status_code == 200

        data = response.json()
        assert data["ingredientName"] == "flour"
        assert len(data["allergens"]) == 2
        assert data["allergens"][0]["allergen"] == "GLUTEN"
        assert data["dataSource"] == "USDA"

        mock_allergen_service.get_ingredient_allergens.assert_called_once_with(
            name="flour"
        )

    async def test_returns_404_for_unknown_ingredient(
        self,
        app: FastAPI,
    ) -> None:
        """Should return 404 when allergen data not found."""
        mock_service = MagicMock()
        mock_service.get_ingredient_allergens = AsyncMock(return_value=None)

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_allergen() -> MagicMock:
            return mock_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_allergen_service] = mock_get_allergen

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/ingredients/unknown/allergens"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_allergen_service, None)

        assert response.status_code == 404

        data = response.json()
        # App transforms HTTPException detail into message
        assert data["error"] == "HTTP_ERROR"
        assert "INGREDIENT_NOT_FOUND" in data["message"]

    async def test_returns_empty_allergens_for_allergen_free_ingredient(
        self,
        app: FastAPI,
    ) -> None:
        """Should return 200 with empty allergens list for allergen-free ingredient."""
        mock_service = MagicMock()
        mock_service.get_ingredient_allergens = AsyncMock(
            return_value=IngredientAllergenResponse(
                ingredient_id=4,
                ingredient_name="chicken",
                allergens=[],
                data_source=AllergenDataSource.USDA,
            )
        )

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_allergen() -> MagicMock:
            return mock_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_allergen_service] = mock_get_allergen

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/ingredients/chicken/allergens"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_allergen_service, None)

        assert response.status_code == 200

        data = response.json()
        assert data["allergens"] == []

    async def test_includes_middleware_headers(
        self,
        ingredient_allergen_client: AsyncClient,
    ) -> None:
        """Should include middleware headers in response."""
        response = await ingredient_allergen_client.get(
            "/api/v1/recipe-scraper/ingredients/flour/allergens"
        )

        assert response.status_code == 200
        assert "x-request-id" in response.headers
        assert "x-process-time" in response.headers


class TestGetRecipeAllergensEndpoint:
    """Integration tests for GET /recipes/{recipeId}/allergens endpoint."""

    @pytest.fixture
    def mock_recipe_client(self) -> MagicMock:
        """Create mock recipe management client."""
        # Import at runtime to avoid circular imports
        from app.services.recipe_management.schemas import (  # noqa: PLC0415
            IngredientUnit,
            RecipeDetailResponse,
            RecipeIngredientResponse,
        )

        mock = MagicMock()
        mock.get_recipe = AsyncMock(
            return_value=RecipeDetailResponse(
                id=1,
                title="Pancakes",
                ingredients=[
                    RecipeIngredientResponse(
                        id=1,
                        ingredient_id=1,
                        ingredient_name="flour",
                        quantity=200.0,
                        unit=IngredientUnit.G,
                    ),
                    RecipeIngredientResponse(
                        id=2,
                        ingredient_id=2,
                        ingredient_name="butter",
                        quantity=50.0,
                        unit=IngredientUnit.G,
                    ),
                ],
            )
        )
        return mock

    @pytest.fixture
    async def recipe_allergen_client(
        self,
        app: FastAPI,
        mock_allergen_service: MagicMock,
        mock_recipe_client: MagicMock,
        sample_recipe_allergen_response: RecipeAllergenResponse,
    ) -> AsyncGenerator[AsyncClient]:
        """Create client with allergen and recipe services mocked."""
        mock_allergen_service.get_recipe_allergens = AsyncMock(
            return_value=sample_recipe_allergen_response
        )

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_allergen() -> MagicMock:
            return mock_allergen_service

        async def mock_get_recipe() -> MagicMock:
            return mock_recipe_client

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_allergen_service] = mock_get_allergen
        app.dependency_overrides[get_recipe_management_client] = mock_get_recipe

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as ac:
                yield ac
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_allergen_service, None)
            app.dependency_overrides.pop(get_recipe_management_client, None)

    async def test_returns_200_with_aggregated_allergens(
        self,
        recipe_allergen_client: AsyncClient,
    ) -> None:
        """Should return 200 with aggregated allergen data."""
        response = await recipe_allergen_client.get(
            "/api/v1/recipe-scraper/recipes/1/allergens"
        )

        assert response.status_code == 200

        data = response.json()
        assert "GLUTEN" in data["contains"]
        assert "MILK" in data["contains"]
        assert "TREE_NUTS" in data["mayContain"]

    async def test_includes_ingredient_details_when_requested(
        self,
        app: FastAPI,
        mock_recipe_client: MagicMock,
    ) -> None:
        """Should include per-ingredient details when includeIngredientDetails=true."""
        mock_allergen = MagicMock()
        mock_allergen.get_recipe_allergens = AsyncMock(
            return_value=RecipeAllergenResponse(
                contains=[Allergen.GLUTEN],
                may_contain=[],
                allergens=[],
                ingredient_details={
                    "flour": IngredientAllergenResponse(
                        ingredient_name="flour",
                        allergens=[AllergenInfo(allergen=Allergen.GLUTEN)],
                    )
                },
            )
        )

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_allergen() -> MagicMock:
            return mock_allergen

        async def mock_get_recipe() -> MagicMock:
            return mock_recipe_client

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_allergen_service] = mock_get_allergen
        app.dependency_overrides[get_recipe_management_client] = mock_get_recipe

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/recipes/1/allergens",
                    params={"includeIngredientDetails": "true"},
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_allergen_service, None)
            app.dependency_overrides.pop(get_recipe_management_client, None)

        assert response.status_code == 200

        data = response.json()
        assert "ingredientDetails" in data
        assert "flour" in data["ingredientDetails"]

    async def test_returns_404_for_nonexistent_recipe(
        self,
        app: FastAPI,
        mock_allergen_service: MagicMock,
    ) -> None:
        """Should return 404 when recipe not found."""
        mock_recipe = MagicMock()
        mock_recipe.get_recipe = AsyncMock(
            side_effect=RecipeManagementNotFoundError("Recipe not found")
        )

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_allergen() -> MagicMock:
            return mock_allergen_service

        async def mock_get_recipe() -> MagicMock:
            return mock_recipe

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_allergen_service] = mock_get_allergen
        app.dependency_overrides[get_recipe_management_client] = mock_get_recipe

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/recipes/999/allergens"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_allergen_service, None)
            app.dependency_overrides.pop(get_recipe_management_client, None)

        assert response.status_code == 404

    async def test_returns_503_when_recipe_service_unavailable(
        self,
        app: FastAPI,
        mock_allergen_service: MagicMock,
    ) -> None:
        """Should return 503 when recipe management service unavailable."""
        mock_recipe = MagicMock()
        mock_recipe.get_recipe = AsyncMock(
            side_effect=RecipeManagementUnavailableError("Service unavailable")
        )

        async def mock_get_current_user() -> CurrentUser:
            return MOCK_USER

        async def mock_get_allergen() -> MagicMock:
            return mock_allergen_service

        async def mock_get_recipe() -> MagicMock:
            return mock_recipe

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_allergen_service] = mock_get_allergen
        app.dependency_overrides[get_recipe_management_client] = mock_get_recipe

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/recipes/1/allergens"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_allergen_service, None)
            app.dependency_overrides.pop(get_recipe_management_client, None)

        assert response.status_code == 503


class TestAllergenEndpointAuthentication:
    """Tests for authentication on allergen endpoints."""

    async def test_returns_401_without_auth(
        self,
        app: FastAPI,
        mock_allergen_service: MagicMock,
    ) -> None:
        """Should return 401 when not authenticated."""
        # Don't override get_current_user - let default auth kick in
        app.dependency_overrides[get_allergen_service] = lambda: mock_allergen_service

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/ingredients/flour/allergens"
                )
        finally:
            app.dependency_overrides.pop(get_allergen_service, None)

        # Should get 401 or 403 depending on auth mode
        assert response.status_code in [401, 403]

    async def test_returns_403_without_permission(
        self,
        app: FastAPI,
        mock_allergen_service: MagicMock,
    ) -> None:
        """Should return 403 when user lacks required permission."""
        user_without_permission = CurrentUser(
            id="test-user-no-perms",
            roles=[],
            permissions=[],
        )

        async def mock_get_current_user() -> CurrentUser:
            return user_without_permission

        async def mock_get_allergen() -> MagicMock:
            return mock_allergen_service

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_allergen_service] = mock_get_allergen

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/recipe-scraper/ingredients/flour/allergens"
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_allergen_service, None)

        assert response.status_code == 403
