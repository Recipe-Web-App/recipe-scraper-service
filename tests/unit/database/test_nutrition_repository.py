"""Unit tests for NutritionRepository.

Tests cover:
- Getting nutrition data by ingredient name
- Getting nutrition data by multiple ingredient names
- Getting nutrition data by FDC ID
- Handling missing data
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database.repositories.nutrition import (
    MacronutrientsData,
    MineralsData,
    NutritionData,
    NutritionRepository,
    VitaminsData,
)


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_pool() -> MagicMock:
    """Create a mock asyncpg pool."""
    pool = MagicMock()
    pool.close = AsyncMock()

    # Mock connection context manager
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.fetch = AsyncMock(return_value=[])

    pool.acquire = MagicMock(return_value=AsyncMock())
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    return pool


@pytest.fixture
def repository(mock_pool: MagicMock) -> NutritionRepository:
    """Create repository with mock pool."""
    return NutritionRepository(pool=mock_pool)


@pytest.fixture
def sample_nutrition_row() -> dict:
    """Create a sample database row with full nutrition data."""
    return {
        "ingredient_id": 1,
        "ingredient_name": "chicken breast",
        "fdc_id": 171077,
        "usda_food_description": "Chicken, broilers or fryers, breast",
        "serving_size_g": Decimal("100.00"),
        "data_source": "USDA",
        # Macronutrients
        "calories_kcal": Decimal("165.000"),
        "protein_g": Decimal("31.000"),
        "carbs_g": Decimal("0.000"),
        "fat_g": Decimal("3.600"),
        "saturated_fat_g": Decimal("1.000"),
        "trans_fat_g": None,
        "monounsaturated_fat_g": Decimal("1.200"),
        "polyunsaturated_fat_g": Decimal("0.800"),
        "cholesterol_mg": Decimal("85.000"),
        "sodium_mg": Decimal("74.000"),
        "fiber_g": Decimal("0.000"),
        "sugar_g": Decimal("0.000"),
        "added_sugar_g": None,
        # Vitamins
        "vitamin_a_mcg": Decimal("6.000"),
        "vitamin_b6_mcg": Decimal("600.000"),
        "vitamin_b12_mcg": Decimal("0.340"),
        "vitamin_c_mcg": Decimal("0.000"),
        "vitamin_d_mcg": Decimal("0.100"),
        "vitamin_e_mcg": Decimal("400.000"),
        "vitamin_k_mcg": Decimal("0.000"),
        # Minerals
        "calcium_mg": Decimal("15.000"),
        "iron_mg": Decimal("1.000"),
        "magnesium_mg": Decimal("29.000"),
        "potassium_mg": Decimal("256.000"),
        "zinc_mg": Decimal("1.000"),
    }


class TestNutritionDataModels:
    """Tests for NutritionData Pydantic models."""

    def test_macronutrients_data_defaults(self) -> None:
        """Should have None defaults for all fields."""
        data = MacronutrientsData()
        assert data.calories_kcal is None
        assert data.protein_g is None

    def test_vitamins_data_defaults(self) -> None:
        """Should have None defaults for all fields."""
        data = VitaminsData()
        assert data.vitamin_a_mcg is None
        assert data.vitamin_c_mcg is None

    def test_minerals_data_defaults(self) -> None:
        """Should have None defaults for all fields."""
        data = MineralsData()
        assert data.calcium_mg is None
        assert data.iron_mg is None

    def test_nutrition_data_with_nested_models(self) -> None:
        """Should create NutritionData with nested models."""
        data = NutritionData(
            ingredient_id=1,
            ingredient_name="test",
            macronutrients=MacronutrientsData(calories_kcal=Decimal(100)),
            vitamins=VitaminsData(vitamin_c_mcg=Decimal(50)),
            minerals=MineralsData(iron_mg=Decimal(2)),
        )
        assert data.ingredient_id == 1
        assert data.macronutrients is not None
        assert data.macronutrients.calories_kcal == Decimal(100)


class TestGetByIngredientName:
    """Tests for get_by_ingredient_name method."""

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(
        self,
        repository: NutritionRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Should return None when ingredient not found."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)

        result = await repository.get_by_ingredient_name("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_nutrition_data_when_found(
        self,
        repository: NutritionRepository,
        mock_pool: MagicMock,
        sample_nutrition_row: dict,
    ) -> None:
        """Should return NutritionData when ingredient found."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=sample_nutrition_row)
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)

        result = await repository.get_by_ingredient_name("chicken breast")

        assert result is not None
        assert result.ingredient_name == "chicken breast"
        assert result.fdc_id == 171077
        assert result.macronutrients is not None
        assert result.macronutrients.calories_kcal == Decimal("165.000")
        assert result.macronutrients.protein_g == Decimal("31.000")
        assert result.vitamins is not None
        assert result.minerals is not None

    @pytest.mark.asyncio
    async def test_handles_null_nutrition_profile(
        self,
        repository: NutritionRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Should handle ingredient with no nutrition profile."""
        row = {
            "ingredient_id": 1,
            "ingredient_name": "unknown",
            "fdc_id": None,
            "usda_food_description": None,
            "serving_size_g": None,
            "data_source": None,
            # All nutrition data is None
            "calories_kcal": None,
            "protein_g": None,
            "carbs_g": None,
            "fat_g": None,
            "saturated_fat_g": None,
            "trans_fat_g": None,
            "monounsaturated_fat_g": None,
            "polyunsaturated_fat_g": None,
            "cholesterol_mg": None,
            "sodium_mg": None,
            "fiber_g": None,
            "sugar_g": None,
            "added_sugar_g": None,
            "vitamin_a_mcg": None,
            "vitamin_b6_mcg": None,
            "vitamin_b12_mcg": None,
            "vitamin_c_mcg": None,
            "vitamin_d_mcg": None,
            "vitamin_e_mcg": None,
            "vitamin_k_mcg": None,
            "calcium_mg": None,
            "iron_mg": None,
            "magnesium_mg": None,
            "potassium_mg": None,
            "zinc_mg": None,
        }
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=row)
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)

        result = await repository.get_by_ingredient_name("unknown")

        assert result is not None
        assert result.ingredient_name == "unknown"
        assert result.macronutrients is None
        assert result.vitamins is None
        assert result.minerals is None
        # Defaults should be applied
        assert result.serving_size_g == Decimal("100.00")
        assert result.data_source == "USDA"


class TestGetByIngredientNames:
    """Tests for get_by_ingredient_names method."""

    @pytest.mark.asyncio
    async def test_returns_empty_dict_for_empty_list(
        self,
        repository: NutritionRepository,
    ) -> None:
        """Should return empty dict for empty input."""
        result = await repository.get_by_ingredient_names([])

        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_dict_with_found_ingredients(
        self,
        repository: NutritionRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Should return dict mapping names to NutritionData."""
        rows = [
            {
                "ingredient_id": 1,
                "ingredient_name": "chicken",
                "fdc_id": 171077,
                "usda_food_description": "Chicken",
                "serving_size_g": Decimal("100.00"),
                "data_source": "USDA",
                "calories_kcal": Decimal("165.000"),
                "protein_g": Decimal("31.000"),
                "carbs_g": None,
                "fat_g": None,
                "saturated_fat_g": None,
                "trans_fat_g": None,
                "monounsaturated_fat_g": None,
                "polyunsaturated_fat_g": None,
                "cholesterol_mg": None,
                "sodium_mg": None,
                "fiber_g": None,
                "sugar_g": None,
                "added_sugar_g": None,
                "vitamin_a_mcg": None,
                "vitamin_b6_mcg": None,
                "vitamin_b12_mcg": None,
                "vitamin_c_mcg": None,
                "vitamin_d_mcg": None,
                "vitamin_e_mcg": None,
                "vitamin_k_mcg": None,
                "calcium_mg": None,
                "iron_mg": None,
                "magnesium_mg": None,
                "potassium_mg": None,
                "zinc_mg": None,
            },
            {
                "ingredient_id": 2,
                "ingredient_name": "rice",
                "fdc_id": 168880,
                "usda_food_description": "Rice",
                "serving_size_g": Decimal("100.00"),
                "data_source": "USDA",
                "calories_kcal": Decimal("130.000"),
                "protein_g": Decimal("2.700"),
                "carbs_g": Decimal("28.000"),
                "fat_g": None,
                "saturated_fat_g": None,
                "trans_fat_g": None,
                "monounsaturated_fat_g": None,
                "polyunsaturated_fat_g": None,
                "cholesterol_mg": None,
                "sodium_mg": None,
                "fiber_g": None,
                "sugar_g": None,
                "added_sugar_g": None,
                "vitamin_a_mcg": None,
                "vitamin_b6_mcg": None,
                "vitamin_b12_mcg": None,
                "vitamin_c_mcg": None,
                "vitamin_d_mcg": None,
                "vitamin_e_mcg": None,
                "vitamin_k_mcg": None,
                "calcium_mg": None,
                "iron_mg": None,
                "magnesium_mg": None,
                "potassium_mg": None,
                "zinc_mg": None,
            },
        ]

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=rows)
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)

        result = await repository.get_by_ingredient_names(["chicken", "rice", "beef"])

        assert "chicken" in result
        assert "rice" in result
        assert "beef" not in result  # Not in mock response
        assert result["chicken"].macronutrients is not None
        assert result["chicken"].macronutrients.calories_kcal == Decimal("165.000")
        assert result["rice"].macronutrients is not None
        assert result["rice"].macronutrients.carbs_g == Decimal("28.000")


class TestGetByFdcId:
    """Tests for get_by_fdc_id method."""

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(
        self,
        repository: NutritionRepository,
        mock_pool: MagicMock,
    ) -> None:
        """Should return None when FDC ID not found."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)

        result = await repository.get_by_fdc_id(999999)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_nutrition_data_when_found(
        self,
        repository: NutritionRepository,
        mock_pool: MagicMock,
        sample_nutrition_row: dict,
    ) -> None:
        """Should return NutritionData when FDC ID found."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=sample_nutrition_row)
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)

        result = await repository.get_by_fdc_id(171077)

        assert result is not None
        assert result.fdc_id == 171077
        assert result.ingredient_name == "chicken breast"


class TestRepositoryPoolAccess:
    """Tests for repository pool access."""

    def test_uses_injected_pool(self, mock_pool: MagicMock) -> None:
        """Should use injected pool when provided."""
        repo = NutritionRepository(pool=mock_pool)

        assert repo.pool is mock_pool

    def test_uses_global_pool_when_not_injected(self) -> None:
        """Should raise when no pool injected and global not initialized."""
        repo = NutritionRepository()

        with pytest.raises(RuntimeError, match="not initialized"):
            _ = repo.pool
