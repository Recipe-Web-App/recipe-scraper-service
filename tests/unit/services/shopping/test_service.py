"""Unit tests for ShoppingService.

Tests cover:
- Getting ingredient shopping info
- Two-tier pricing lookup (Tier 1 → Tier 2 fallback)
- Price calculation based on quantity
- Cache behavior
- Error handling
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import orjson
import pytest

from app.database.repositories.shopping import IngredientDetails, PricingData
from app.schemas.enums import IngredientUnit
from app.schemas.ingredient import Ingredient, Quantity
from app.services.shopping.constants import TIER_1_CONFIDENCE, TIER_2_CONFIDENCE
from app.services.shopping.exceptions import IngredientNotFoundError
from app.services.shopping.service import ShoppingService


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_cache_client() -> AsyncMock:
    """Create a mock Redis cache client."""
    client = AsyncMock()
    client.get.return_value = None
    client.setex.return_value = True
    return client


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Create a mock PricingRepository."""
    repo = AsyncMock()
    repo.get_ingredient_details.return_value = None
    repo.get_price_by_ingredient_id.return_value = None
    repo.get_price_by_food_group.return_value = None
    return repo


@pytest.fixture
def mock_nutrition_repository() -> AsyncMock:
    """Create a mock NutritionRepository."""
    repo = AsyncMock()
    repo.get_portion_weight.return_value = None
    return repo


@pytest.fixture
def service(
    mock_cache_client: AsyncMock,
    mock_repository: AsyncMock,
    mock_nutrition_repository: AsyncMock,
) -> ShoppingService:
    """Create ShoppingService with mocked dependencies."""
    svc = ShoppingService(
        cache_client=mock_cache_client,
        repository=mock_repository,
        nutrition_repository=mock_nutrition_repository,
    )
    # Manually set initialized flag and converter
    svc._initialized = True
    svc._converter = MagicMock()
    svc._converter.to_grams = AsyncMock(return_value=Decimal(100))
    return svc


@pytest.fixture
def sample_ingredient_details() -> IngredientDetails:
    """Create sample ingredient details."""
    return IngredientDetails(
        ingredient_id=123,
        name="chicken breast",
        food_group="POULTRY",
    )


@pytest.fixture
def sample_tier1_pricing() -> PricingData:
    """Create sample Tier 1 pricing data."""
    return PricingData(
        price_per_100g=Decimal("0.5250"),
        currency="USD",
        data_source="USDA_MEAT",
        source_year=2024,
        tier=1,
    )


@pytest.fixture
def sample_tier2_pricing() -> PricingData:
    """Create sample Tier 2 pricing data."""
    return PricingData(
        price_per_100g=Decimal("0.4500"),
        currency="USD",
        data_source="USDA_FMAP",
        tier=2,
    )


class TestGetIngredientShoppingInfo:
    """Tests for get_ingredient_shopping_info method."""

    async def test_returns_tier1_pricing(
        self,
        service: ShoppingService,
        mock_repository: AsyncMock,
        sample_ingredient_details: IngredientDetails,
        sample_tier1_pricing: PricingData,
    ) -> None:
        """Test returns Tier 1 pricing when available."""
        mock_repository.get_ingredient_details.return_value = sample_ingredient_details
        mock_repository.get_price_by_ingredient_id.return_value = sample_tier1_pricing

        result = await service.get_ingredient_shopping_info(ingredient_id=123)

        assert result.ingredient_name == "chicken breast"
        assert result.estimated_price == "0.52"  # 100g * 0.5250/100g
        assert result.price_confidence == float(TIER_1_CONFIDENCE)
        assert result.data_source == "USDA_MEAT"
        assert result.currency == "USD"

    async def test_falls_back_to_tier2_pricing(
        self,
        service: ShoppingService,
        mock_repository: AsyncMock,
        sample_ingredient_details: IngredientDetails,
        sample_tier2_pricing: PricingData,
    ) -> None:
        """Test falls back to Tier 2 when Tier 1 not available."""
        mock_repository.get_ingredient_details.return_value = sample_ingredient_details
        mock_repository.get_price_by_ingredient_id.return_value = None
        mock_repository.get_price_by_food_group.return_value = sample_tier2_pricing

        result = await service.get_ingredient_shopping_info(ingredient_id=123)

        assert result.ingredient_name == "chicken breast"
        assert result.estimated_price == "0.45"  # 100g * 0.4500/100g
        assert result.price_confidence == float(TIER_2_CONFIDENCE)
        assert result.data_source == "USDA_FMAP"
        mock_repository.get_price_by_food_group.assert_called_once_with("POULTRY")

    async def test_returns_null_price_when_no_pricing_data(
        self,
        service: ShoppingService,
        mock_repository: AsyncMock,
        sample_ingredient_details: IngredientDetails,
    ) -> None:
        """Test returns null price when neither Tier 1 nor Tier 2 available."""
        mock_repository.get_ingredient_details.return_value = sample_ingredient_details
        mock_repository.get_price_by_ingredient_id.return_value = None
        mock_repository.get_price_by_food_group.return_value = None

        result = await service.get_ingredient_shopping_info(ingredient_id=123)

        assert result.ingredient_name == "chicken breast"
        assert result.estimated_price is None
        assert result.price_confidence is None
        assert result.data_source is None

    async def test_raises_error_when_ingredient_not_found(
        self,
        service: ShoppingService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test raises IngredientNotFoundError when ingredient doesn't exist."""
        mock_repository.get_ingredient_details.return_value = None

        with pytest.raises(IngredientNotFoundError) as exc_info:
            await service.get_ingredient_shopping_info(ingredient_id=999)

        assert "Ingredient not found: 999" in str(exc_info.value)
        assert exc_info.value.ingredient_id == 999

    async def test_calculates_price_for_quantity(
        self,
        service: ShoppingService,
        mock_repository: AsyncMock,
        sample_ingredient_details: IngredientDetails,
        sample_tier1_pricing: PricingData,
    ) -> None:
        """Test calculates price based on provided quantity."""
        mock_repository.get_ingredient_details.return_value = sample_ingredient_details
        mock_repository.get_price_by_ingredient_id.return_value = sample_tier1_pricing
        # Mock conversion: 2 cups = 500g
        service._converter.to_grams.return_value = Decimal(500)

        quantity = Quantity(amount=2.0, measurement=IngredientUnit.CUP)
        result = await service.get_ingredient_shopping_info(
            ingredient_id=123,
            quantity=quantity,
        )

        # 500g * 0.5250/100g = 2.625
        assert result.estimated_price == "2.62"
        assert result.quantity.amount == 2.0
        assert result.quantity.measurement == IngredientUnit.CUP

    async def test_defaults_to_100g_when_no_quantity(
        self,
        service: ShoppingService,
        mock_repository: AsyncMock,
        sample_ingredient_details: IngredientDetails,
        sample_tier1_pricing: PricingData,
    ) -> None:
        """Test defaults to 100g when no quantity provided."""
        mock_repository.get_ingredient_details.return_value = sample_ingredient_details
        mock_repository.get_price_by_ingredient_id.return_value = sample_tier1_pricing

        result = await service.get_ingredient_shopping_info(ingredient_id=123)

        assert result.quantity.amount == 100.0
        assert result.quantity.measurement == IngredientUnit.G


class TestCaching:
    """Tests for caching behavior."""

    async def test_returns_cached_result(
        self,
        service: ShoppingService,
        mock_cache_client: AsyncMock,
        mock_repository: AsyncMock,
    ) -> None:
        """Test returns cached result without hitting repository."""
        cached_response = {
            "ingredientName": "chicken breast",
            "quantity": {"amount": 100.0, "measurement": "G"},
            "estimatedPrice": "0.52",
            "priceConfidence": 0.95,
            "dataSource": "USDA_MEAT",
            "currency": "USD",
        }
        mock_cache_client.get.return_value = orjson.dumps(cached_response)

        result = await service.get_ingredient_shopping_info(ingredient_id=123)

        assert result.ingredient_name == "chicken breast"
        assert result.estimated_price == "0.52"
        mock_repository.get_ingredient_details.assert_not_called()

    async def test_caches_result_after_fetch(
        self,
        service: ShoppingService,
        mock_cache_client: AsyncMock,
        mock_repository: AsyncMock,
        sample_ingredient_details: IngredientDetails,
        sample_tier1_pricing: PricingData,
    ) -> None:
        """Test caches result after fetching from repository."""
        mock_cache_client.get.return_value = None
        mock_repository.get_ingredient_details.return_value = sample_ingredient_details
        mock_repository.get_price_by_ingredient_id.return_value = sample_tier1_pricing

        await service.get_ingredient_shopping_info(ingredient_id=123)

        mock_cache_client.setex.assert_called_once()
        call_args = mock_cache_client.setex.call_args
        assert "shopping:123:100.0:G" in call_args[0][0]


class TestPriceCalculation:
    """Tests for price calculation logic."""

    def test_calculate_price_100g(self, service: ShoppingService) -> None:
        """Test price calculation for 100g."""
        price = service._calculate_price(
            price_per_100g=Decimal("0.5250"),
            grams=Decimal(100),
        )
        assert price == Decimal("0.5250")

    def test_calculate_price_500g(self, service: ShoppingService) -> None:
        """Test price calculation for 500g."""
        price = service._calculate_price(
            price_per_100g=Decimal("0.5250"),
            grams=Decimal(500),
        )
        assert price == Decimal("2.625")

    def test_calculate_price_50g(self, service: ShoppingService) -> None:
        """Test price calculation for 50g."""
        price = service._calculate_price(
            price_per_100g=Decimal("0.5250"),
            grams=Decimal(50),
        )
        assert price == Decimal("0.2625")


class TestCacheKey:
    """Tests for cache key generation."""

    def test_cache_key_format(self, service: ShoppingService) -> None:
        """Test cache key format."""
        quantity = Quantity(amount=2.5, measurement=IngredientUnit.CUP)
        key = service._make_cache_key(123, quantity)
        assert key == "shopping:123:2.5:CUP"

    def test_cache_key_with_grams(self, service: ShoppingService) -> None:
        """Test cache key with gram quantity."""
        quantity = Quantity(amount=100.0, measurement=IngredientUnit.G)
        key = service._make_cache_key(456, quantity)
        assert key == "shopping:456:100.0:G"


class TestServiceLifecycle:
    """Tests for service initialization and shutdown."""

    async def test_initialize_sets_initialized_flag(self) -> None:
        """Test initialize sets the initialized flag."""
        service = ShoppingService()

        with patch("app.services.shopping.service.get_cache_client") as mock_cache:
            mock_cache.return_value = AsyncMock()
            await service.initialize()

        assert service._initialized is True

    async def test_shutdown_clears_initialized_flag(
        self,
        service: ShoppingService,
    ) -> None:
        """Test shutdown clears the initialized flag."""
        assert service._initialized is True

        await service.shutdown()

        assert service._initialized is False

    async def test_raises_error_when_not_initialized(self) -> None:
        """Test raises error when service not initialized."""
        service = ShoppingService()

        with pytest.raises(RuntimeError, match="ShoppingService not initialized"):
            await service.get_ingredient_shopping_info(ingredient_id=123)


class TestGetRecipeShoppingInfo:
    """Tests for get_recipe_shopping_info method."""

    async def test_aggregates_all_ingredients(
        self,
        service: ShoppingService,
        mock_repository: AsyncMock,
        sample_ingredient_details: IngredientDetails,
        sample_tier1_pricing: PricingData,
    ) -> None:
        """Test aggregates shopping info for all ingredients."""
        mock_repository.get_ingredient_details.return_value = sample_ingredient_details
        mock_repository.get_price_by_ingredient_id.return_value = sample_tier1_pricing

        ingredients = [
            Ingredient(
                ingredient_id=1,
                name="chicken",
                quantity=Quantity(amount=100, measurement=IngredientUnit.G),
            ),
            Ingredient(
                ingredient_id=2,
                name="rice",
                quantity=Quantity(amount=100, measurement=IngredientUnit.G),
            ),
        ]

        result = await service.get_recipe_shopping_info(
            recipe_id=123, ingredients=ingredients
        )

        assert result.recipe_id == 123
        assert len(result.ingredients) == 2
        assert "chicken" in result.ingredients
        assert "rice" in result.ingredients

    async def test_calculates_total_cost(
        self,
        service: ShoppingService,
        mock_repository: AsyncMock,
        sample_ingredient_details: IngredientDetails,
        sample_tier1_pricing: PricingData,
    ) -> None:
        """Test calculates total cost from all ingredients."""
        mock_repository.get_ingredient_details.return_value = sample_ingredient_details
        mock_repository.get_price_by_ingredient_id.return_value = sample_tier1_pricing

        ingredients = [
            Ingredient(
                ingredient_id=1,
                name="chicken",
                quantity=Quantity(amount=100, measurement=IngredientUnit.G),
            ),
            Ingredient(
                ingredient_id=2,
                name="rice",
                quantity=Quantity(amount=100, measurement=IngredientUnit.G),
            ),
        ]

        result = await service.get_recipe_shopping_info(
            recipe_id=123, ingredients=ingredients
        )

        # 2 ingredients at 0.52 each = 1.04
        assert result.total_estimated_cost == "1.04"

    async def test_handles_missing_prices(
        self,
        service: ShoppingService,
        mock_repository: AsyncMock,
        sample_ingredient_details: IngredientDetails,
    ) -> None:
        """Test handles ingredients with no pricing data."""
        # First ingredient has no pricing
        no_price_details = IngredientDetails(
            ingredient_id=1,
            name="exotic spice",
            food_group=None,
        )
        mock_repository.get_ingredient_details.side_effect = [
            no_price_details,
            sample_ingredient_details,
        ]
        mock_repository.get_price_by_ingredient_id.side_effect = [
            None,
            PricingData(
                price_per_100g=Decimal("0.50"),
                currency="USD",
                data_source="USDA_MEAT",
                tier=1,
            ),
        ]

        ingredients = [
            Ingredient(
                ingredient_id=1,
                name="exotic spice",
                quantity=Quantity(amount=100, measurement=IngredientUnit.G),
            ),
            Ingredient(
                ingredient_id=2,
                name="chicken",
                quantity=Quantity(amount=100, measurement=IngredientUnit.G),
            ),
        ]

        result = await service.get_recipe_shopping_info(
            recipe_id=123, ingredients=ingredients
        )

        assert result.missing_ingredients == [1]
        assert result.total_estimated_cost == "0.50"  # Only chicken price

    async def test_handles_ingredient_not_found(
        self,
        service: ShoppingService,
        mock_repository: AsyncMock,
        sample_ingredient_details: IngredientDetails,
        sample_tier1_pricing: PricingData,
    ) -> None:
        """Test handles ingredients that don't exist in database."""
        mock_repository.get_ingredient_details.side_effect = [
            None,  # First ingredient not found
            sample_ingredient_details,
        ]
        mock_repository.get_price_by_ingredient_id.return_value = sample_tier1_pricing

        ingredients = [
            Ingredient(
                ingredient_id=999,
                name="unknown",
                quantity=Quantity(amount=100, measurement=IngredientUnit.G),
            ),
            Ingredient(
                ingredient_id=2,
                name="chicken",
                quantity=Quantity(amount=100, measurement=IngredientUnit.G),
            ),
        ]

        result = await service.get_recipe_shopping_info(
            recipe_id=123, ingredients=ingredients
        )

        assert result.missing_ingredients is not None
        assert 999 in result.missing_ingredients
        assert "chicken" in result.ingredients
        assert "unknown" not in result.ingredients

    async def test_empty_ingredients_returns_zero(
        self,
        service: ShoppingService,
    ) -> None:
        """Test empty ingredient list returns zero total."""
        result = await service.get_recipe_shopping_info(recipe_id=123, ingredients=[])

        assert result.recipe_id == 123
        assert result.ingredients == {}
        assert result.total_estimated_cost == "0.00"
        assert result.missing_ingredients is None

    async def test_skips_ingredients_without_id(
        self,
        service: ShoppingService,
        mock_repository: AsyncMock,
        sample_ingredient_details: IngredientDetails,
        sample_tier1_pricing: PricingData,
    ) -> None:
        """Test skips ingredients without ID or name."""
        mock_repository.get_ingredient_details.return_value = sample_ingredient_details
        mock_repository.get_price_by_ingredient_id.return_value = sample_tier1_pricing

        ingredients = [
            Ingredient(ingredient_id=None, name="no-id"),  # Missing ID
            Ingredient(ingredient_id=1, name=None),  # Missing name
            Ingredient(
                ingredient_id=2,
                name="chicken",
                quantity=Quantity(amount=100, measurement=IngredientUnit.G),
            ),
        ]

        result = await service.get_recipe_shopping_info(
            recipe_id=123, ingredients=ingredients
        )

        assert len(result.ingredients) == 1
        assert "chicken" in result.ingredients


class TestShoppingServiceInitialization:
    """Tests for service initialization edge cases."""

    async def test_initialize_handles_cache_unavailable(self) -> None:
        """Test initialize handles cache unavailability gracefully."""
        from unittest.mock import patch

        # Create service without injected dependencies
        service = ShoppingService()

        with (
            patch(
                "app.services.shopping.service.get_cache_client",
                side_effect=Exception("Redis unavailable"),
            ),
            patch("app.services.shopping.service.PricingRepository") as mock_repo_class,
            patch(
                "app.services.shopping.service.NutritionRepository"
            ) as mock_nutrition_class,
            patch("app.services.shopping.service.UnitConverter"),
        ):
            mock_repo_class.return_value = MagicMock()
            mock_nutrition_class.return_value = MagicMock()

            await service.initialize()

            # Should be initialized even without cache
            assert service._initialized is True
            assert service._cache_client is None

    async def test_initialize_creates_repositories_when_none(self) -> None:
        """Test initialize creates repositories when not injected."""
        from unittest.mock import patch

        service = ShoppingService()

        with (
            patch(
                "app.services.shopping.service.get_cache_client",
                new_callable=AsyncMock,
            ) as mock_get_cache,
            patch("app.services.shopping.service.PricingRepository") as mock_repo_class,
            patch(
                "app.services.shopping.service.NutritionRepository"
            ) as mock_nutrition_class,
            patch(
                "app.services.shopping.service.UnitConverter"
            ) as mock_converter_class,
        ):
            mock_cache = MagicMock()
            mock_get_cache.return_value = mock_cache
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_nutrition_repo = MagicMock()
            mock_nutrition_class.return_value = mock_nutrition_repo
            mock_converter_class.return_value = MagicMock()

            await service.initialize()

            mock_repo_class.assert_called_once()
            mock_nutrition_class.assert_called_once()
            assert service._repository is mock_repo
            assert service._nutrition_repository is mock_nutrition_repo


class TestShoppingServiceNotInitialized:
    """Tests for service methods when not initialized."""

    async def test_get_recipe_shopping_info_raises_when_not_initialized(self) -> None:
        """Test get_recipe_shopping_info raises when not initialized."""
        service = ShoppingService()

        with pytest.raises(RuntimeError, match="not initialized"):
            await service.get_recipe_shopping_info(recipe_id=1, ingredients=[])


class TestShoppingServiceCacheEdgeCases:
    """Tests for cache-related edge cases."""

    async def test_get_from_cache_returns_none_when_cache_unavailable(
        self,
        service: ShoppingService,
    ) -> None:
        """Test _get_from_cache returns None when cache client is None."""
        service._cache_client = None

        result = await service._get_from_cache("some_key")

        assert result is None

    async def test_get_from_cache_handles_exception(
        self,
        service: ShoppingService,
    ) -> None:
        """Test _get_from_cache handles exceptions gracefully."""
        service._cache_client = AsyncMock()
        service._cache_client.get = AsyncMock(side_effect=Exception("Connection lost"))

        result = await service._get_from_cache("some_key")

        assert result is None

    async def test_cache_result_does_nothing_when_cache_unavailable(
        self,
        service: ShoppingService,
    ) -> None:
        """Test _cache_result does nothing when cache client is None."""
        service._cache_client = None

        # Should not raise
        await service._cache_result("some_key", MagicMock())

    async def test_cache_result_handles_exception(
        self,
        service: ShoppingService,
    ) -> None:
        """Test _cache_result handles exceptions gracefully."""
        service._cache_client = AsyncMock()
        service._cache_client.setex = AsyncMock(side_effect=Exception("Write failed"))

        mock_response = MagicMock()
        mock_response.model_dump.return_value = {"test": "data"}

        # Should not raise
        await service._cache_result("some_key", mock_response)
