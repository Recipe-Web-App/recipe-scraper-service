"""Unit tests for recipe allergen info endpoint.

Tests cover:
- Get recipe allergen info endpoint
- Query parameter validation
- Error handling for various failure scenarios
- 206 Partial Content for missing ingredients
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import orjson
import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.recipes import get_recipe_allergens
from app.schemas.allergen import (
    AllergenDataSource,
    AllergenInfo,
    AllergenPresenceType,
    IngredientAllergenResponse,
    RecipeAllergenResponse,
)
from app.schemas.enums import Allergen
from app.services.recipe_management.exceptions import (
    RecipeManagementError,
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


class TestGetRecipeAllergens:
    """Tests for get_recipe_allergens endpoint."""

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
    def mock_allergen_service(self) -> MagicMock:
        """Create a mock allergen service."""
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
                    ingredient_name="milk",
                    quantity=200.0,
                    unit=RecipeIngredientUnit.ML,
                ),
            ],
        )

    @pytest.fixture
    def sample_allergen_result(self) -> RecipeAllergenResponse:
        """Create sample allergen result with all data."""
        return RecipeAllergenResponse(
            contains=[Allergen.GLUTEN, Allergen.MILK],
            may_contain=[Allergen.TREE_NUTS],
            allergens=[
                AllergenInfo(
                    allergen=Allergen.GLUTEN,
                    presence_type=AllergenPresenceType.CONTAINS,
                    confidence_score=0.95,
                ),
                AllergenInfo(
                    allergen=Allergen.MILK,
                    presence_type=AllergenPresenceType.CONTAINS,
                    confidence_score=0.99,
                ),
                AllergenInfo(
                    allergen=Allergen.TREE_NUTS,
                    presence_type=AllergenPresenceType.MAY_CONTAIN,
                    confidence_score=0.70,
                ),
            ],
            missing_ingredients=[],
        )

    @pytest.fixture
    def sample_partial_allergen_result(self) -> RecipeAllergenResponse:
        """Create sample allergen result with missing ingredients."""
        return RecipeAllergenResponse(
            contains=[Allergen.GLUTEN],
            may_contain=[],
            allergens=[
                AllergenInfo(
                    allergen=Allergen.GLUTEN,
                    presence_type=AllergenPresenceType.CONTAINS,
                    confidence_score=0.95,
                ),
            ],
            missing_ingredients=[102],  # milk is missing
        )

    @pytest.mark.asyncio
    async def test_returns_200_with_complete_data(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_allergen_service: MagicMock,
        sample_recipe_response: RecipeDetailResponse,
        sample_allergen_result: RecipeAllergenResponse,
    ) -> None:
        """Should return 200 when all ingredients have allergen data."""
        mock_recipe_client.get_recipe = AsyncMock(return_value=sample_recipe_response)
        mock_allergen_service.get_recipe_allergens = AsyncMock(
            return_value=sample_allergen_result
        )

        result = await get_recipe_allergens(
            recipe_id=123,
            user=mock_user,
            recipe_client=mock_recipe_client,
            allergen_service=mock_allergen_service,
            request=mock_request,
            include_ingredient_details=False,
        )

        assert result.status_code == 200
        mock_recipe_client.get_recipe.assert_called_once_with(123, "test-token-123")
        mock_allergen_service.get_recipe_allergens.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_206_when_ingredients_missing(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_allergen_service: MagicMock,
        sample_recipe_response: RecipeDetailResponse,
        sample_partial_allergen_result: RecipeAllergenResponse,
    ) -> None:
        """Should return 206 with header when some ingredients missing."""
        mock_recipe_client.get_recipe = AsyncMock(return_value=sample_recipe_response)
        mock_allergen_service.get_recipe_allergens = AsyncMock(
            return_value=sample_partial_allergen_result
        )

        result = await get_recipe_allergens(
            recipe_id=123,
            user=mock_user,
            recipe_client=mock_recipe_client,
            allergen_service=mock_allergen_service,
            request=mock_request,
            include_ingredient_details=False,
        )

        assert result.status_code == 206
        assert "X-Partial-Content" in result.headers
        assert result.headers["X-Partial-Content"] == "102"

    @pytest.mark.asyncio
    async def test_raises_404_when_recipe_not_found(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_allergen_service: MagicMock,
    ) -> None:
        """Should raise 404 when recipe not found."""
        mock_recipe_client.get_recipe = AsyncMock(
            side_effect=RecipeManagementNotFoundError("Recipe not found")
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_recipe_allergens(
                recipe_id=999,
                user=mock_user,
                recipe_client=mock_recipe_client,
                allergen_service=mock_allergen_service,
                request=mock_request,
                include_ingredient_details=False,
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
        mock_allergen_service: MagicMock,
    ) -> None:
        """Should raise 503 when Recipe Management Service unavailable."""
        mock_recipe_client.get_recipe = AsyncMock(
            side_effect=RecipeManagementUnavailableError("Service unavailable")
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_recipe_allergens(
                recipe_id=123,
                user=mock_user,
                recipe_client=mock_recipe_client,
                allergen_service=mock_allergen_service,
                request=mock_request,
                include_ingredient_details=False,
            )

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["error"] == "SERVICE_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_raises_502_when_downstream_error(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_allergen_service: MagicMock,
    ) -> None:
        """Should raise 502 when Recipe Management Service returns an error."""
        mock_recipe_client.get_recipe = AsyncMock(
            side_effect=RecipeManagementError("Downstream error")
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_recipe_allergens(
                recipe_id=123,
                user=mock_user,
                recipe_client=mock_recipe_client,
                allergen_service=mock_allergen_service,
                request=mock_request,
                include_ingredient_details=False,
            )

        assert exc_info.value.status_code == 502
        assert exc_info.value.detail["error"] == "DOWNSTREAM_ERROR"

    @pytest.mark.asyncio
    async def test_handles_empty_recipe(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_allergen_service: MagicMock,
    ) -> None:
        """Should return empty response for recipe with no ingredients."""
        empty_recipe = RecipeDetailResponse(
            id=123,
            title="Empty Recipe",
            ingredients=[],
        )
        mock_recipe_client.get_recipe = AsyncMock(return_value=empty_recipe)

        result = await get_recipe_allergens(
            recipe_id=123,
            user=mock_user,
            recipe_client=mock_recipe_client,
            allergen_service=mock_allergen_service,
            request=mock_request,
            include_ingredient_details=False,
        )

        assert result.status_code == 200
        # Allergen service should not be called for empty recipe
        mock_allergen_service.get_recipe_allergens.assert_not_called()

    @pytest.mark.asyncio
    async def test_includes_details_when_requested(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_allergen_service: MagicMock,
        sample_recipe_response: RecipeDetailResponse,
    ) -> None:
        """Should include per-ingredient details when includeIngredientDetails is true."""
        result_with_details = RecipeAllergenResponse(
            contains=[Allergen.GLUTEN],
            may_contain=[],
            allergens=[
                AllergenInfo(
                    allergen=Allergen.GLUTEN,
                    presence_type=AllergenPresenceType.CONTAINS,
                ),
            ],
            ingredient_details={
                "flour": IngredientAllergenResponse(
                    ingredient_name="flour",
                    allergens=[
                        AllergenInfo(
                            allergen=Allergen.GLUTEN,
                            presence_type=AllergenPresenceType.CONTAINS,
                        ),
                    ],
                    data_source=AllergenDataSource.USDA,
                ),
            },
            missing_ingredients=[],
        )
        mock_recipe_client.get_recipe = AsyncMock(return_value=sample_recipe_response)
        mock_allergen_service.get_recipe_allergens = AsyncMock(
            return_value=result_with_details
        )

        result = await get_recipe_allergens(
            recipe_id=123,
            user=mock_user,
            recipe_client=mock_recipe_client,
            allergen_service=mock_allergen_service,
            request=mock_request,
            include_ingredient_details=True,
        )

        assert result.status_code == 200

        data = orjson.loads(result.body)
        assert "ingredientDetails" in data
        assert "flour" in data["ingredientDetails"]

        # Verify service was called with include_details=True
        call_args = mock_allergen_service.get_recipe_allergens.call_args
        assert call_args.kwargs["include_details"] is True

    @pytest.mark.asyncio
    async def test_excludes_details_by_default(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_allergen_service: MagicMock,
        sample_recipe_response: RecipeDetailResponse,
        sample_allergen_result: RecipeAllergenResponse,
    ) -> None:
        """Should not include per-ingredient details by default."""
        mock_recipe_client.get_recipe = AsyncMock(return_value=sample_recipe_response)
        mock_allergen_service.get_recipe_allergens = AsyncMock(
            return_value=sample_allergen_result
        )

        result = await get_recipe_allergens(
            recipe_id=123,
            user=mock_user,
            recipe_client=mock_recipe_client,
            allergen_service=mock_allergen_service,
            request=mock_request,
            include_ingredient_details=False,
        )

        assert result.status_code == 200

        # Verify service was called with include_details=False
        call_args = mock_allergen_service.get_recipe_allergens.call_args
        assert call_args.kwargs["include_details"] is False

    @pytest.mark.asyncio
    async def test_forwards_auth_token(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_allergen_service: MagicMock,
        sample_recipe_response: RecipeDetailResponse,
        sample_allergen_result: RecipeAllergenResponse,
    ) -> None:
        """Should forward auth token to recipe client."""
        mock_recipe_client.get_recipe = AsyncMock(return_value=sample_recipe_response)
        mock_allergen_service.get_recipe_allergens = AsyncMock(
            return_value=sample_allergen_result
        )

        await get_recipe_allergens(
            recipe_id=123,
            user=mock_user,
            recipe_client=mock_recipe_client,
            allergen_service=mock_allergen_service,
            request=mock_request,
            include_ingredient_details=False,
        )

        mock_recipe_client.get_recipe.assert_called_once_with(123, "test-token-123")

    @pytest.mark.asyncio
    async def test_transforms_ingredients_correctly(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_allergen_service: MagicMock,
        sample_recipe_response: RecipeDetailResponse,
        sample_allergen_result: RecipeAllergenResponse,
    ) -> None:
        """Should correctly transform recipe ingredients to Ingredient schema."""
        mock_recipe_client.get_recipe = AsyncMock(return_value=sample_recipe_response)
        mock_allergen_service.get_recipe_allergens = AsyncMock(
            return_value=sample_allergen_result
        )

        await get_recipe_allergens(
            recipe_id=123,
            user=mock_user,
            recipe_client=mock_recipe_client,
            allergen_service=mock_allergen_service,
            request=mock_request,
            include_ingredient_details=False,
        )

        # Check that allergen service was called with properly transformed ingredients
        call_args = mock_allergen_service.get_recipe_allergens.call_args
        ingredients = call_args[0][0]

        assert len(ingredients) == 2
        assert ingredients[0].name == "flour"
        assert ingredients[0].ingredient_id == 101
        assert ingredients[1].name == "milk"
        assert ingredients[1].ingredient_id == 102

    @pytest.mark.asyncio
    async def test_response_contains_allergen_lists(
        self,
        mock_user: MagicMock,
        mock_request: MagicMock,
        mock_recipe_client: MagicMock,
        mock_allergen_service: MagicMock,
        sample_recipe_response: RecipeDetailResponse,
        sample_allergen_result: RecipeAllergenResponse,
    ) -> None:
        """Should include contains and mayContain allergen lists."""
        mock_recipe_client.get_recipe = AsyncMock(return_value=sample_recipe_response)
        mock_allergen_service.get_recipe_allergens = AsyncMock(
            return_value=sample_allergen_result
        )

        result = await get_recipe_allergens(
            recipe_id=123,
            user=mock_user,
            recipe_client=mock_recipe_client,
            allergen_service=mock_allergen_service,
            request=mock_request,
            include_ingredient_details=False,
        )

        data = orjson.loads(result.body)

        assert "contains" in data
        assert "mayContain" in data
        assert "GLUTEN" in data["contains"]
        assert "MILK" in data["contains"]
        assert "TREE_NUTS" in data["mayContain"]
