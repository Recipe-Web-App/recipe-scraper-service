"""Unit tests for NutritionService."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import orjson
import pytest

from app.database.repositories.nutrition import (
    MacronutrientsData,
    MineralsData,
    NutritionData,
    VitaminsData,
)
from app.schemas.enums import IngredientUnit
from app.schemas.ingredient import Ingredient, Quantity
from app.services.nutrition.exceptions import ConversionError
from app.services.nutrition.service import NutritionService


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_cache_client() -> MagicMock:
    """Create mock Redis cache client."""
    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    client.setex = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_repository() -> MagicMock:
    """Create mock NutritionRepository."""
    repo = MagicMock()
    repo.get_by_ingredient_name = AsyncMock(return_value=None)
    repo.get_by_ingredient_names = AsyncMock(return_value={})
    repo.get_by_ingredient_name_fuzzy = AsyncMock(return_value=None)
    repo.get_by_ingredient_names_fuzzy = AsyncMock(return_value={})
    repo.get_portion_weight = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def sample_nutrition_data() -> NutritionData:
    """Create sample nutrition data for testing."""
    return NutritionData(
        ingredient_id=1,
        ingredient_name="flour",
        fdc_id=12345,
        usda_food_description="Wheat flour, white, all-purpose",
        serving_size_g=Decimal(100),
        macronutrients=MacronutrientsData(
            calories_kcal=Decimal(364),
            protein_g=Decimal("10.3"),
            carbs_g=Decimal("76.3"),
            fat_g=Decimal("1.0"),
            fiber_g=Decimal("2.7"),
            sugar_g=Decimal("0.3"),
        ),
        vitamins=VitaminsData(
            vitamin_b6_mcg=Decimal(44),
        ),
        minerals=MineralsData(
            calcium_mg=Decimal(15),
            iron_mg=Decimal("4.6"),
        ),
    )


@pytest.fixture
def service(
    mock_cache_client: MagicMock,
    mock_repository: MagicMock,
) -> NutritionService:
    """Create NutritionService with mocked dependencies."""
    return NutritionService(
        cache_client=mock_cache_client,
        repository=mock_repository,
    )


class TestNutritionServiceLifecycle:
    """Tests for service lifecycle methods."""

    async def test_initialize_creates_converter(
        self,
        mock_cache_client: MagicMock,
        mock_repository: MagicMock,
    ) -> None:
        """Should create converter on initialize."""
        service = NutritionService(
            cache_client=mock_cache_client,
            repository=mock_repository,
        )
        assert service._converter is None

        await service.initialize()

        assert service._converter is not None

        await service.shutdown()

    async def test_initialize_uses_injected_repository(
        self,
        mock_cache_client: MagicMock,
        mock_repository: MagicMock,
    ) -> None:
        """Should use injected repository."""
        service = NutritionService(
            cache_client=mock_cache_client,
            repository=mock_repository,
        )
        await service.initialize()

        assert service._repository is mock_repository

        await service.shutdown()

    async def test_shutdown_completes_without_error(
        self,
        service: NutritionService,
    ) -> None:
        """Should shutdown without error."""
        await service.initialize()
        await service.shutdown()  # Should not raise


class TestGetIngredientNutrition:
    """Tests for get_ingredient_nutrition method."""

    async def test_returns_none_when_not_initialized(
        self,
        service: NutritionService,
    ) -> None:
        """Should return None if service not initialized."""
        # Don't call initialize
        quantity = Quantity(amount=100, measurement=IngredientUnit.G)
        result = await service.get_ingredient_nutrition("flour", quantity)
        assert result is None

    async def test_returns_none_when_ingredient_not_found(
        self,
        service: NutritionService,
        mock_repository: MagicMock,
    ) -> None:
        """Should return None when ingredient not in database."""
        await service.initialize()
        mock_repository.get_by_ingredient_name.return_value = None

        quantity = Quantity(amount=100, measurement=IngredientUnit.G)
        result = await service.get_ingredient_nutrition("unknown", quantity)

        assert result is None
        await service.shutdown()

    async def test_returns_scaled_nutrition(
        self,
        service: NutritionService,
        mock_repository: MagicMock,
        sample_nutrition_data: NutritionData,
    ) -> None:
        """Should return nutrition scaled to quantity."""
        await service.initialize()
        mock_repository.get_by_ingredient_name.return_value = sample_nutrition_data

        # 200g = 2x the per-100g values
        quantity = Quantity(amount=200, measurement=IngredientUnit.G)
        result = await service.get_ingredient_nutrition("flour", quantity)

        assert result is not None
        assert result.quantity == quantity
        assert result.macro_nutrients is not None
        # 364 kcal per 100g * 2 = 728 kcal
        assert result.macro_nutrients.calories is not None
        assert result.macro_nutrients.calories.amount == pytest.approx(728, rel=0.01)

        await service.shutdown()

    async def test_returns_half_for_50g(
        self,
        service: NutritionService,
        mock_repository: MagicMock,
        sample_nutrition_data: NutritionData,
    ) -> None:
        """Should scale down for smaller quantities."""
        await service.initialize()
        mock_repository.get_by_ingredient_name.return_value = sample_nutrition_data

        quantity = Quantity(amount=50, measurement=IngredientUnit.G)
        result = await service.get_ingredient_nutrition("flour", quantity)

        assert result is not None
        assert result.macro_nutrients is not None
        # 364 kcal per 100g * 0.5 = 182 kcal
        assert result.macro_nutrients.calories is not None
        assert result.macro_nutrients.calories.amount == pytest.approx(182, rel=0.01)

        await service.shutdown()

    async def test_includes_usda_description(
        self,
        service: NutritionService,
        mock_repository: MagicMock,
        sample_nutrition_data: NutritionData,
    ) -> None:
        """Should include USDA food description in response."""
        await service.initialize()
        mock_repository.get_by_ingredient_name.return_value = sample_nutrition_data

        quantity = Quantity(amount=100, measurement=IngredientUnit.G)
        result = await service.get_ingredient_nutrition("flour", quantity)

        assert result is not None
        assert result.usda_food_description == "Wheat flour, white, all-purpose"

        await service.shutdown()


class TestGetIngredientNutritionCaching:
    """Tests for caching behavior."""

    async def test_cache_hit_skips_database(
        self,
        service: NutritionService,
        mock_cache_client: MagicMock,
        mock_repository: MagicMock,
        sample_nutrition_data: NutritionData,
    ) -> None:
        """Should use cached data and skip database."""
        await service.initialize()

        # Simulate cache hit
        cached_bytes = orjson.dumps(sample_nutrition_data.model_dump(mode="json"))
        mock_cache_client.get.return_value = cached_bytes

        quantity = Quantity(amount=100, measurement=IngredientUnit.G)
        result = await service.get_ingredient_nutrition("flour", quantity)

        assert result is not None
        mock_repository.get_by_ingredient_name.assert_not_called()

        await service.shutdown()

    async def test_cache_miss_queries_database(
        self,
        service: NutritionService,
        mock_cache_client: MagicMock,
        mock_repository: MagicMock,
        sample_nutrition_data: NutritionData,
    ) -> None:
        """Should query database on cache miss."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_repository.get_by_ingredient_name.return_value = sample_nutrition_data

        quantity = Quantity(amount=100, measurement=IngredientUnit.G)
        result = await service.get_ingredient_nutrition("flour", quantity)

        assert result is not None
        mock_repository.get_by_ingredient_name.assert_called_once_with("flour")

        await service.shutdown()

    async def test_caches_database_result(
        self,
        service: NutritionService,
        mock_cache_client: MagicMock,
        mock_repository: MagicMock,
        sample_nutrition_data: NutritionData,
    ) -> None:
        """Should cache result after database query."""
        await service.initialize()

        mock_cache_client.get.return_value = None
        mock_repository.get_by_ingredient_name.return_value = sample_nutrition_data

        quantity = Quantity(amount=100, measurement=IngredientUnit.G)
        await service.get_ingredient_nutrition("flour", quantity)

        mock_cache_client.setex.assert_called_once()
        call_args = mock_cache_client.setex.call_args
        assert "nutrition:flour" in call_args[0][0]

        await service.shutdown()


class TestGetRecipeNutrition:
    """Tests for get_recipe_nutrition method."""

    async def test_aggregates_multiple_ingredients(
        self,
        service: NutritionService,
        mock_repository: MagicMock,
        sample_nutrition_data: NutritionData,
    ) -> None:
        """Should aggregate nutrition from multiple ingredients."""
        await service.initialize()

        # Create second ingredient
        sugar_data = NutritionData(
            ingredient_id=2,
            ingredient_name="sugar",
            macronutrients=MacronutrientsData(
                calories_kcal=Decimal(387),
                carbs_g=Decimal(100),
            ),
        )

        mock_repository.get_by_ingredient_names.return_value = {
            "flour": sample_nutrition_data,
            "sugar": sugar_data,
        }

        ingredients = [
            Ingredient(
                ingredient_id=1,
                name="flour",
                quantity=Quantity(amount=100, measurement=IngredientUnit.G),
            ),
            Ingredient(
                ingredient_id=2,
                name="sugar",
                quantity=Quantity(amount=100, measurement=IngredientUnit.G),
            ),
        ]

        result = await service.get_recipe_nutrition(ingredients)

        assert result.ingredients is not None
        assert len(result.ingredients) == 2
        assert "flour" in result.ingredients
        assert "sugar" in result.ingredients

        # Total should be sum of both
        assert result.total.macro_nutrients is not None
        # 364 + 387 = 751 kcal
        assert result.total.macro_nutrients.calories is not None
        assert result.total.macro_nutrients.calories.amount == pytest.approx(
            751, rel=0.01
        )

        await service.shutdown()

    async def test_tracks_missing_ingredients(
        self,
        service: NutritionService,
        mock_repository: MagicMock,
        sample_nutrition_data: NutritionData,
    ) -> None:
        """Should track ingredients not found in database."""
        await service.initialize()

        mock_repository.get_by_ingredient_names.return_value = {
            "flour": sample_nutrition_data,
            # "mystery ingredient" not in result
        }

        ingredients = [
            Ingredient(
                ingredient_id=1,
                name="flour",
                quantity=Quantity(amount=100, measurement=IngredientUnit.G),
            ),
            Ingredient(
                ingredient_id=99,
                name="mystery ingredient",
                quantity=Quantity(amount=50, measurement=IngredientUnit.G),
            ),
        ]

        result = await service.get_recipe_nutrition(ingredients)

        assert result.missing_ingredients is not None
        assert 99 in result.missing_ingredients

        await service.shutdown()

    async def test_handles_ingredient_without_name(
        self,
        service: NutritionService,
        mock_repository: MagicMock,
    ) -> None:
        """Should track ingredients without names as missing."""
        await service.initialize()

        mock_repository.get_by_ingredient_names.return_value = {}

        ingredients = [
            Ingredient(
                ingredient_id=42,
                name=None,  # No name
                quantity=Quantity(amount=100, measurement=IngredientUnit.G),
            ),
        ]

        result = await service.get_recipe_nutrition(ingredients)

        assert result.missing_ingredients is not None
        assert 42 in result.missing_ingredients

        await service.shutdown()

    async def test_uses_default_quantity_when_missing(
        self,
        service: NutritionService,
        mock_repository: MagicMock,
        sample_nutrition_data: NutritionData,
    ) -> None:
        """Should use 100g default when quantity is missing."""
        await service.initialize()

        mock_repository.get_by_ingredient_names.return_value = {
            "flour": sample_nutrition_data,
        }

        ingredients = [
            Ingredient(
                ingredient_id=1,
                name="flour",
                quantity=None,  # No quantity specified
            ),
        ]

        result = await service.get_recipe_nutrition(ingredients)

        assert result.ingredients is not None
        flour_result = result.ingredients.get("flour")
        assert flour_result is not None
        # Should use 100g default
        assert flour_result.quantity.amount == 100
        assert flour_result.quantity.measurement == IngredientUnit.G

        await service.shutdown()

    async def test_calculates_total_grams(
        self,
        service: NutritionService,
        mock_repository: MagicMock,
        sample_nutrition_data: NutritionData,
    ) -> None:
        """Should calculate total weight in grams."""
        await service.initialize()

        mock_repository.get_by_ingredient_names.return_value = {
            "flour": sample_nutrition_data,
        }

        ingredients = [
            Ingredient(
                ingredient_id=1,
                name="flour",
                quantity=Quantity(amount=250, measurement=IngredientUnit.G),
            ),
        ]

        result = await service.get_recipe_nutrition(ingredients)

        assert result.total.quantity.amount == 250
        assert result.total.quantity.measurement == IngredientUnit.G

        await service.shutdown()


class TestErrorHandling:
    """Tests for error handling."""

    async def test_conversion_error_raises(
        self,
        service: NutritionService,
        mock_repository: MagicMock,
        sample_nutrition_data: NutritionData,
    ) -> None:
        """Should raise ConversionError when conversion fails."""
        await service.initialize()
        mock_repository.get_by_ingredient_name.return_value = sample_nutrition_data

        # Patch converter to raise
        with patch.object(
            service._converter,
            "to_grams",
            side_effect=ConversionError("Test error"),
        ):
            quantity = Quantity(amount=1, measurement=IngredientUnit.G)
            with pytest.raises(ConversionError):
                await service.get_ingredient_nutrition("flour", quantity)

        await service.shutdown()

    async def test_recipe_skips_ingredient_on_conversion_error(
        self,
        service: NutritionService,
        mock_repository: MagicMock,
        sample_nutrition_data: NutritionData,
    ) -> None:
        """Should skip ingredient and mark as missing on conversion error."""
        await service.initialize()

        mock_repository.get_by_ingredient_names.return_value = {
            "flour": sample_nutrition_data,
        }

        # Make converter fail for this specific call
        original_to_grams = service._converter.to_grams
        error_msg = "Test error"

        async def failing_to_grams(quantity: Quantity, name: str) -> Decimal:
            if name == "flour":
                raise ConversionError(error_msg)
            return await original_to_grams(quantity, name)

        with patch.object(service._converter, "to_grams", side_effect=failing_to_grams):
            ingredients = [
                Ingredient(
                    ingredient_id=1,
                    name="flour",
                    quantity=Quantity(amount=100, measurement=IngredientUnit.G),
                ),
            ]

            result = await service.get_recipe_nutrition(ingredients)

            # Flour should be in missing due to conversion error
            assert result.missing_ingredients is not None
            assert 1 in result.missing_ingredients

        await service.shutdown()
