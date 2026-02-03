"""Unit tests for recipe shopping info endpoint.

Tests cover:
- Get recipe shopping info endpoint
- Error handling for various failure scenarios
- 206 Partial Content for missing ingredient prices
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.recipes import get_recipe_shopping_info
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


pytestmark = pytest.mark.unit


class TestGetRecipeShoppingInfo:
    """Tests for get_recipe_shopping_info endpoint."""

    @pytest.fixture
    def mock_user(self) -> MagicMock:
        """Create a mock authenticated user."""
        user = MagicMock()
        user.id = "user-123"
        return user

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        """Create a mock HTTP request with auth header."""
        request = MagicMock()
        request.headers.get.return_value = "Bearer test-token-123"
        return request

    @pytest.fixture
    def mock_recipe_client(self) -> MagicMock:
        """Create a mock recipe management client."""
        return MagicMock()

    @pytest.fixture
    def mock_shopping_service(self) -> MagicMock:
        """Create a mock shopping service."""
        return MagicMock()

    @pytest.fixture
    def sample_recipe_response(self) -> RecipeDetailResponse:
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
    def sample_shopping_result(self) -> RecipeShoppingInfoResponse:
        """Create sample shopping result with all data."""
        return RecipeShoppingInfoResponse(
            recipe_id=123,
            ingredients={
                "flour": IngredientShoppingInfoResponse(
                    ingredient_name="flour",
                    quantity=Quantity(amount=250.0, measurement=IngredientUnit.G),
                    estimated_price="0.62",
                    price_confidence=0.95,
                    data_source="USDA_FVP",
                    currency="USD",
                ),
                "sugar": IngredientShoppingInfoResponse(
                    ingredient_name="sugar",
                    quantity=Quantity(amount=100.0, measurement=IngredientUnit.G),
                    estimated_price="0.15",
                    price_confidence=0.95,
                    data_source="USDA_FVP",
                    currency="USD",
                ),
            },
            total_estimated_cost="0.77",
            missing_ingredients=None,
        )

    async def test_returns_200_with_complete_shopping_info(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_shopping_service: MagicMock,
        sample_recipe_response: RecipeDetailResponse,
        sample_shopping_result: RecipeShoppingInfoResponse,
    ) -> None:
        """Test returns 200 when all ingredients have pricing."""
        mock_recipe_client.get_recipe = AsyncMock(return_value=sample_recipe_response)
        mock_shopping_service.get_recipe_shopping_info = AsyncMock(
            return_value=sample_shopping_result
        )

        response = await get_recipe_shopping_info(
            recipe_id=123,
            user=mock_user,
            recipe_client=mock_recipe_client,
            shopping_service=mock_shopping_service,
            request=mock_request,
        )

        assert response.status_code == 200
        mock_recipe_client.get_recipe.assert_called_once_with(123, "test-token-123")

    async def test_returns_206_with_partial_content(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_shopping_service: MagicMock,
        sample_recipe_response: RecipeDetailResponse,
    ) -> None:
        """Test returns 206 when some ingredients missing prices."""
        partial_result = RecipeShoppingInfoResponse(
            recipe_id=123,
            ingredients={
                "flour": IngredientShoppingInfoResponse(
                    ingredient_name="flour",
                    quantity=Quantity(amount=250.0, measurement=IngredientUnit.G),
                    estimated_price="0.62",
                    price_confidence=0.95,
                    data_source="USDA_FVP",
                    currency="USD",
                ),
            },
            total_estimated_cost="0.62",
            missing_ingredients=[102],
        )
        mock_recipe_client.get_recipe = AsyncMock(return_value=sample_recipe_response)
        mock_shopping_service.get_recipe_shopping_info = AsyncMock(
            return_value=partial_result
        )

        response = await get_recipe_shopping_info(
            recipe_id=123,
            user=mock_user,
            recipe_client=mock_recipe_client,
            shopping_service=mock_shopping_service,
            request=mock_request,
        )

        assert response.status_code == 206
        assert response.headers["X-Partial-Content"] == "102"

    async def test_returns_404_when_recipe_not_found(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_shopping_service: MagicMock,
    ) -> None:
        """Test returns 404 when recipe doesn't exist."""
        mock_recipe_client.get_recipe = AsyncMock(
            side_effect=RecipeManagementNotFoundError("Recipe not found")
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_recipe_shopping_info(
                recipe_id=999,
                user=mock_user,
                recipe_client=mock_recipe_client,
                shopping_service=mock_shopping_service,
                request=mock_request,
            )

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail)

    async def test_returns_503_when_service_unavailable(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_shopping_service: MagicMock,
    ) -> None:
        """Test returns 503 when Recipe Management Service unavailable."""
        mock_recipe_client.get_recipe = AsyncMock(
            side_effect=RecipeManagementUnavailableError("Service unavailable")
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_recipe_shopping_info(
                recipe_id=123,
                user=mock_user,
                recipe_client=mock_recipe_client,
                shopping_service=mock_shopping_service,
                request=mock_request,
            )

        assert exc_info.value.status_code == 503

    async def test_handles_empty_recipe(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_shopping_service: MagicMock,
    ) -> None:
        """Test handles recipe with no ingredients."""
        empty_recipe = RecipeDetailResponse(
            id=123,
            title="Empty Recipe",
            slug="empty-recipe",
            ingredients=[],
        )
        mock_recipe_client.get_recipe = AsyncMock(return_value=empty_recipe)

        response = await get_recipe_shopping_info(
            recipe_id=123,
            user=mock_user,
            recipe_client=mock_recipe_client,
            shopping_service=mock_shopping_service,
            request=mock_request,
        )

        assert response.status_code == 200
        # Shopping service should not be called for empty recipe
        mock_shopping_service.get_recipe_shopping_info.assert_not_called()
