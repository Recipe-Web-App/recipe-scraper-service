"""Unit tests for PricingRepository.

Tests cover:
- Getting pricing data by ingredient ID (Tier 1)
- Getting pricing data by food group (Tier 2 fallback)
- Getting ingredient details
- Handling missing data and tables
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database.repositories.shopping import (
    IngredientDetails,
    PricingData,
    PricingRepository,
)


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_pool() -> MagicMock:
    """Create a mock asyncpg pool."""
    pool = MagicMock()
    pool.close = AsyncMock()

    # Mock connection context manager
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.fetch = AsyncMock(return_value=[])

    pool.acquire = MagicMock(return_value=AsyncMock())
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    return pool


@pytest.fixture
def repository(mock_pool: MagicMock) -> PricingRepository:
    """Create repository with mock pool."""
    return PricingRepository(pool=mock_pool)


@pytest.fixture
def sample_tier1_pricing_row() -> dict:
    """Create a sample Tier 1 pricing database row."""
    return {
        "price_per_100g": Decimal("0.5250"),
        "currency": "USD",
        "data_source": "USDA_FVP",
        "source_year": 2024,
    }


@pytest.fixture
def sample_tier2_pricing_row() -> dict:
    """Create a sample Tier 2 (food group) pricing database row."""
    return {
        "price_per_100g": Decimal("0.4500"),
        "currency": "USD",
        "data_source": "USDA_FMAP",
    }


@pytest.fixture
def sample_ingredient_details_row() -> dict:
    """Create a sample ingredient details database row."""
    return {
        "ingredient_id": 123,
        "name": "chicken breast",
        "food_group": "POULTRY",
    }


class TestPricingDataModel:
    """Tests for PricingData Pydantic model."""

    def test_tier1_pricing_data(self) -> None:
        """Test creating Tier 1 pricing data."""
        data = PricingData(
            price_per_100g=Decimal("0.5250"),
            currency="USD",
            data_source="USDA_FVP",
            source_year=2024,
            tier=1,
        )
        assert data.price_per_100g == Decimal("0.5250")
        assert data.currency == "USD"
        assert data.data_source == "USDA_FVP"
        assert data.source_year == 2024
        assert data.tier == 1

    def test_tier2_pricing_data(self) -> None:
        """Test creating Tier 2 pricing data (no source_year)."""
        data = PricingData(
            price_per_100g=Decimal("0.4500"),
            currency="USD",
            data_source="USDA_FMAP",
            tier=2,
        )
        assert data.price_per_100g == Decimal("0.4500")
        assert data.source_year is None
        assert data.tier == 2


class TestIngredientDetailsModel:
    """Tests for IngredientDetails Pydantic model."""

    def test_ingredient_details_with_food_group(self) -> None:
        """Test creating ingredient details with food group."""
        details = IngredientDetails(
            ingredient_id=123,
            name="chicken breast",
            food_group="POULTRY",
        )
        assert details.ingredient_id == 123
        assert details.name == "chicken breast"
        assert details.food_group == "POULTRY"

    def test_ingredient_details_without_food_group(self) -> None:
        """Test creating ingredient details without food group."""
        details = IngredientDetails(
            ingredient_id=456,
            name="mystery ingredient",
        )
        assert details.ingredient_id == 456
        assert details.name == "mystery ingredient"
        assert details.food_group is None


class TestGetPriceByIngredientId:
    """Tests for Tier 1 pricing lookup."""

    async def test_returns_pricing_data_when_found(
        self,
        repository: PricingRepository,
        mock_pool: MagicMock,
        sample_tier1_pricing_row: dict,
    ) -> None:
        """Test successful Tier 1 pricing lookup."""
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.return_value = sample_tier1_pricing_row

        result = await repository.get_price_by_ingredient_id(123)

        assert result is not None
        assert result.price_per_100g == Decimal("0.5250")
        assert result.currency == "USD"
        assert result.data_source == "USDA_FVP"
        assert result.source_year == 2024
        assert result.tier == 1

    async def test_returns_none_when_not_found(
        self,
        repository: PricingRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Test Tier 1 lookup returns None when ingredient not in pricing table."""
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.return_value = None

        result = await repository.get_price_by_ingredient_id(999)

        assert result is None

    async def test_handles_missing_table_gracefully(
        self,
        repository: PricingRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Test graceful handling when ingredient_pricing table doesn't exist."""
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.side_effect = Exception(
            'relation "recipe_manager.ingredient_pricing" does not exist'
        )

        result = await repository.get_price_by_ingredient_id(123)

        assert result is None


class TestGetPriceByFoodGroup:
    """Tests for Tier 2 pricing lookup."""

    async def test_returns_pricing_data_when_found(
        self,
        repository: PricingRepository,
        mock_pool: MagicMock,
        sample_tier2_pricing_row: dict,
    ) -> None:
        """Test successful Tier 2 pricing lookup."""
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.return_value = sample_tier2_pricing_row

        result = await repository.get_price_by_food_group("VEGETABLES")

        assert result is not None
        assert result.price_per_100g == Decimal("0.4500")
        assert result.currency == "USD"
        assert result.data_source == "USDA_FMAP"
        assert result.source_year is None
        assert result.tier == 2

    async def test_returns_none_when_food_group_not_found(
        self,
        repository: PricingRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Test Tier 2 lookup returns None when food group not in pricing table."""
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.return_value = None

        result = await repository.get_price_by_food_group("UNKNOWN")

        assert result is None

    async def test_handles_invalid_enum_gracefully(
        self,
        repository: PricingRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Test graceful handling when food group is not a valid enum value."""
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.side_effect = Exception(
            'invalid input value for enum recipe_manager.food_group_enum: "INVALID"'
        )

        result = await repository.get_price_by_food_group("INVALID")

        assert result is None

    async def test_handles_missing_table_gracefully(
        self,
        repository: PricingRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Test graceful handling when food_group_pricing table doesn't exist."""
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.side_effect = Exception(
            'relation "recipe_manager.food_group_pricing" does not exist'
        )

        result = await repository.get_price_by_food_group("VEGETABLES")

        assert result is None


class TestGetIngredientDetails:
    """Tests for ingredient details lookup."""

    async def test_returns_details_when_found(
        self,
        repository: PricingRepository,
        mock_pool: MagicMock,
        sample_ingredient_details_row: dict,
    ) -> None:
        """Test successful ingredient details lookup."""
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.return_value = sample_ingredient_details_row

        result = await repository.get_ingredient_details(123)

        assert result is not None
        assert result.ingredient_id == 123
        assert result.name == "chicken breast"
        assert result.food_group == "POULTRY"

    async def test_returns_none_when_not_found(
        self,
        repository: PricingRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Test returns None when ingredient doesn't exist."""
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.return_value = None

        result = await repository.get_ingredient_details(999)

        assert result is None

    async def test_returns_details_without_food_group(
        self,
        repository: PricingRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Test returns details when ingredient has no nutrition profile."""
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.return_value = {
            "ingredient_id": 456,
            "name": "mystery ingredient",
            "food_group": None,
        }

        result = await repository.get_ingredient_details(456)

        assert result is not None
        assert result.ingredient_id == 456
        assert result.name == "mystery ingredient"
        assert result.food_group is None

    async def test_handles_missing_table_gracefully(
        self,
        repository: PricingRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Test graceful handling when ingredients table doesn't exist."""
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.side_effect = Exception(
            'relation "recipe_manager.ingredients" does not exist'
        )

        result = await repository.get_ingredient_details(123)

        assert result is None

    async def test_reraises_unexpected_exceptions(
        self,
        repository: PricingRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Test that unexpected exceptions are re-raised."""
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.side_effect = Exception("Connection timeout")

        with pytest.raises(Exception, match="Connection timeout"):
            await repository.get_ingredient_details(123)


class TestGetPriceByIngredientIdErrorHandling:
    """Additional tests for error handling in Tier 1 pricing lookup."""

    async def test_reraises_unexpected_exceptions(
        self,
        repository: PricingRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Test that unexpected exceptions are re-raised."""
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.side_effect = Exception("Connection pool exhausted")

        with pytest.raises(Exception, match="Connection pool exhausted"):
            await repository.get_price_by_ingredient_id(123)


class TestGetPriceByFoodGroupErrorHandling:
    """Additional tests for error handling in Tier 2 pricing lookup."""

    async def test_reraises_unexpected_exceptions(
        self,
        repository: PricingRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Test that unexpected exceptions are re-raised."""
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.side_effect = Exception("Database connection lost")

        with pytest.raises(Exception, match="Database connection lost"):
            await repository.get_price_by_food_group("VEGETABLES")


class TestPricingRepositoryPool:
    """Tests for pool property fallback behavior."""

    def test_uses_provided_pool(self, mock_pool: MagicMock) -> None:
        """Test that provided pool is used."""
        repo = PricingRepository(pool=mock_pool)
        assert repo.pool is mock_pool

    def test_falls_back_to_global_pool(self) -> None:
        """Test that pool property falls back to get_database_pool()."""
        from unittest.mock import patch

        mock_global_pool = MagicMock()

        with patch(
            "app.database.repositories.shopping.get_database_pool",
            return_value=mock_global_pool,
        ):
            repo = PricingRepository()  # No pool provided
            assert repo.pool is mock_global_pool
