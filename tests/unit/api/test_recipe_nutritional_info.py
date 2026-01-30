"""Unit tests for recipe nutritional info endpoint.

Tests cover:
- Get recipe nutritional info endpoint
- Query parameter validation
- Error handling for various failure scenarios
- 206 Partial Content for missing ingredients
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import orjson
import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.recipes import get_recipe_nutritional_info
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


pytestmark = pytest.mark.unit


class TestGetRecipeNutritionalInfo:
    """Tests for get_recipe_nutritional_info endpoint."""

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
    def mock_nutrition_service(self) -> MagicMock:
        """Create a mock nutrition service."""
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
    def sample_nutrition_result(self) -> RecipeNutritionalInfoResponse:
        """Create sample nutrition result with all data."""
        return RecipeNutritionalInfoResponse(
            ingredients={
                "101": IngredientNutritionalInfoResponse(
                    quantity=Quantity(amount=250.0, measurement=IngredientUnit.G),
                    macro_nutrients=MacroNutrients(
                        calories=NutrientValue(
                            amount=910.0, measurement=NutrientUnit.KILOCALORIE
                        ),
                        carbs=NutrientValue(
                            amount=190.75, measurement=NutrientUnit.GRAM
                        ),
                        protein=NutrientValue(
                            amount=25.75, measurement=NutrientUnit.GRAM
                        ),
                        fats=Fats(
                            total=NutrientValue(
                                amount=2.5, measurement=NutrientUnit.GRAM
                            )
                        ),
                    ),
                ),
            },
            missing_ingredients=None,
            total=IngredientNutritionalInfoResponse(
                quantity=Quantity(amount=350.0, measurement=IngredientUnit.G),
                macro_nutrients=MacroNutrients(
                    calories=NutrientValue(
                        amount=1300.0, measurement=NutrientUnit.KILOCALORIE
                    ),
                    carbs=NutrientValue(amount=290.0, measurement=NutrientUnit.GRAM),
                    protein=NutrientValue(amount=30.0, measurement=NutrientUnit.GRAM),
                    fats=Fats(
                        total=NutrientValue(amount=3.0, measurement=NutrientUnit.GRAM)
                    ),
                ),
            ),
        )

    @pytest.fixture
    def sample_partial_nutrition_result(self) -> RecipeNutritionalInfoResponse:
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
            missing_ingredients=[102],  # sugar is missing
            total=IngredientNutritionalInfoResponse(
                quantity=Quantity(amount=250.0, measurement=IngredientUnit.G),
                macro_nutrients=MacroNutrients(
                    calories=NutrientValue(
                        amount=910.0, measurement=NutrientUnit.KILOCALORIE
                    ),
                ),
            ),
        )

    @pytest.mark.asyncio
    async def test_returns_200_with_complete_data(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_nutrition_service: MagicMock,
        sample_recipe_response: RecipeDetailResponse,
        sample_nutrition_result: RecipeNutritionalInfoResponse,
    ) -> None:
        """Should return 200 when all ingredients have nutrition data."""
        mock_recipe_client.get_recipe = AsyncMock(return_value=sample_recipe_response)
        mock_nutrition_service.get_recipe_nutrition = AsyncMock(
            return_value=sample_nutrition_result
        )

        result = await get_recipe_nutritional_info(
            recipe_id=123,
            user=mock_user,
            recipe_client=mock_recipe_client,
            nutrition_service=mock_nutrition_service,
            request=mock_request,
            include_total=True,
            include_ingredients=False,
        )

        assert result.status_code == 200
        mock_recipe_client.get_recipe.assert_called_once_with(123, "test-token-123")
        mock_nutrition_service.get_recipe_nutrition.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_206_when_ingredients_missing(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_nutrition_service: MagicMock,
        sample_recipe_response: RecipeDetailResponse,
        sample_partial_nutrition_result: RecipeNutritionalInfoResponse,
    ) -> None:
        """Should return 206 with header when some ingredients missing."""
        mock_recipe_client.get_recipe = AsyncMock(return_value=sample_recipe_response)
        mock_nutrition_service.get_recipe_nutrition = AsyncMock(
            return_value=sample_partial_nutrition_result
        )

        result = await get_recipe_nutritional_info(
            recipe_id=123,
            user=mock_user,
            recipe_client=mock_recipe_client,
            nutrition_service=mock_nutrition_service,
            request=mock_request,
            include_total=True,
            include_ingredients=True,
        )

        assert result.status_code == 206
        assert "X-Partial-Content" in result.headers
        assert result.headers["X-Partial-Content"] == "102"

    @pytest.mark.asyncio
    async def test_raises_400_when_both_flags_false(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should raise 400 when both includeTotal and includeIngredients are false."""
        with pytest.raises(HTTPException) as exc_info:
            await get_recipe_nutritional_info(
                recipe_id=123,
                user=mock_user,
                recipe_client=mock_recipe_client,
                nutrition_service=mock_nutrition_service,
                request=mock_request,
                include_total=False,
                include_ingredients=False,
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "BAD_REQUEST"
        assert "includeTotal" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_raises_404_when_recipe_not_found(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should raise 404 when recipe not found."""
        mock_recipe_client.get_recipe = AsyncMock(
            side_effect=RecipeManagementNotFoundError("Recipe not found")
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_recipe_nutritional_info(
                recipe_id=999,
                user=mock_user,
                recipe_client=mock_recipe_client,
                nutrition_service=mock_nutrition_service,
                request=mock_request,
                include_total=True,
                include_ingredients=False,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error"] == "NOT_FOUND"
        assert "999" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_raises_503_when_service_unavailable(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should raise 503 when Recipe Management Service unavailable."""
        mock_recipe_client.get_recipe = AsyncMock(
            side_effect=RecipeManagementUnavailableError("Service unavailable")
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_recipe_nutritional_info(
                recipe_id=123,
                user=mock_user,
                recipe_client=mock_recipe_client,
                nutrition_service=mock_nutrition_service,
                request=mock_request,
                include_total=True,
                include_ingredients=False,
            )

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["error"] == "SERVICE_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_handles_empty_recipe(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_nutrition_service: MagicMock,
    ) -> None:
        """Should return zero totals for recipe with no ingredients."""
        empty_recipe = RecipeDetailResponse(
            id=123,
            title="Empty Recipe",
            ingredients=[],
        )
        mock_recipe_client.get_recipe = AsyncMock(return_value=empty_recipe)

        result = await get_recipe_nutritional_info(
            recipe_id=123,
            user=mock_user,
            recipe_client=mock_recipe_client,
            nutrition_service=mock_nutrition_service,
            request=mock_request,
            include_total=True,
            include_ingredients=False,
        )

        assert result.status_code == 200
        # Nutrition service should not be called for empty recipe
        mock_nutrition_service.get_recipe_nutrition.assert_not_called()

    @pytest.mark.asyncio
    async def test_filters_response_include_total_only(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_nutrition_service: MagicMock,
        sample_recipe_response: RecipeDetailResponse,
        sample_nutrition_result: RecipeNutritionalInfoResponse,
    ) -> None:
        """Should only include total when includeIngredients is false."""
        mock_recipe_client.get_recipe = AsyncMock(return_value=sample_recipe_response)
        mock_nutrition_service.get_recipe_nutrition = AsyncMock(
            return_value=sample_nutrition_result
        )

        result = await get_recipe_nutritional_info(
            recipe_id=123,
            user=mock_user,
            recipe_client=mock_recipe_client,
            nutrition_service=mock_nutrition_service,
            request=mock_request,
            include_total=True,
            include_ingredients=False,
        )

        assert result.status_code == 200

        data = orjson.loads(result.body)
        assert "total" in data
        assert "ingredients" not in data

    @pytest.mark.asyncio
    async def test_filters_response_include_ingredients_only(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_nutrition_service: MagicMock,
        sample_recipe_response: RecipeDetailResponse,
        sample_nutrition_result: RecipeNutritionalInfoResponse,
    ) -> None:
        """Should only include ingredients when includeTotal is false."""
        mock_recipe_client.get_recipe = AsyncMock(return_value=sample_recipe_response)
        mock_nutrition_service.get_recipe_nutrition = AsyncMock(
            return_value=sample_nutrition_result
        )

        result = await get_recipe_nutritional_info(
            recipe_id=123,
            user=mock_user,
            recipe_client=mock_recipe_client,
            nutrition_service=mock_nutrition_service,
            request=mock_request,
            include_total=False,
            include_ingredients=True,
        )

        assert result.status_code == 200

        data = orjson.loads(result.body)
        assert "ingredients" in data
        assert "total" not in data

    @pytest.mark.asyncio
    async def test_forwards_auth_token(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_nutrition_service: MagicMock,
        sample_recipe_response: RecipeDetailResponse,
        sample_nutrition_result: RecipeNutritionalInfoResponse,
    ) -> None:
        """Should forward auth token to recipe client."""
        mock_recipe_client.get_recipe = AsyncMock(return_value=sample_recipe_response)
        mock_nutrition_service.get_recipe_nutrition = AsyncMock(
            return_value=sample_nutrition_result
        )

        await get_recipe_nutritional_info(
            recipe_id=123,
            user=mock_user,
            recipe_client=mock_recipe_client,
            nutrition_service=mock_nutrition_service,
            request=mock_request,
            include_total=True,
            include_ingredients=False,
        )

        mock_recipe_client.get_recipe.assert_called_once_with(123, "test-token-123")

    @pytest.mark.asyncio
    async def test_transforms_ingredients_correctly(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_nutrition_service: MagicMock,
        sample_recipe_response: RecipeDetailResponse,
        sample_nutrition_result: RecipeNutritionalInfoResponse,
    ) -> None:
        """Should correctly transform recipe ingredients to Ingredient schema."""
        mock_recipe_client.get_recipe = AsyncMock(return_value=sample_recipe_response)
        mock_nutrition_service.get_recipe_nutrition = AsyncMock(
            return_value=sample_nutrition_result
        )

        await get_recipe_nutritional_info(
            recipe_id=123,
            user=mock_user,
            recipe_client=mock_recipe_client,
            nutrition_service=mock_nutrition_service,
            request=mock_request,
            include_total=True,
            include_ingredients=True,
        )

        # Check that nutrition service was called with properly transformed ingredients
        call_args = mock_nutrition_service.get_recipe_nutrition.call_args
        ingredients = call_args[0][0]

        assert len(ingredients) == 2
        assert ingredients[0].name == "flour"
        assert ingredients[0].quantity.amount == 250.0
        assert ingredients[0].quantity.measurement == IngredientUnit.G
        assert ingredients[1].name == "sugar"
        assert ingredients[1].quantity.amount == 100.0
