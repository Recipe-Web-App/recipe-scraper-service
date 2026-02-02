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
from app.schemas.ingredient import Quantity
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
