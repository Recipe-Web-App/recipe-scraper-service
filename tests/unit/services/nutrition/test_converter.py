"""Unit tests for UnitConverter."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.enums import IngredientUnit
from app.schemas.ingredient import Quantity
from app.services.nutrition.converter import UnitConverter


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_repository() -> MagicMock:
    """Create mock NutritionRepository."""
    repo = MagicMock()
    repo.get_portion_weight = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def converter() -> UnitConverter:
    """Create UnitConverter without repository (uses fallbacks)."""
    return UnitConverter()


@pytest.fixture
def converter_with_repo(mock_repository: MagicMock) -> UnitConverter:
    """Create UnitConverter with mocked repository."""
    return UnitConverter(nutrition_repository=mock_repository)


class TestWeightConversions:
    """Tests for weight unit conversions using Pint."""

    async def test_grams_to_grams(self, converter: UnitConverter) -> None:
        """Should return same value for grams."""
        quantity = Quantity(amount=100, measurement=IngredientUnit.G)
        result = await converter.to_grams(quantity, "flour")
        assert result == Decimal(100)

    async def test_kilograms_to_grams(self, converter: UnitConverter) -> None:
        """Should convert kilograms to grams."""
        quantity = Quantity(amount=1, measurement=IngredientUnit.KG)
        result = await converter.to_grams(quantity, "flour")
        assert result == Decimal(1000)

    async def test_ounces_to_grams(self, converter: UnitConverter) -> None:
        """Should convert ounces to grams."""
        quantity = Quantity(amount=1, measurement=IngredientUnit.OZ)
        result = await converter.to_grams(quantity, "butter")
        # 1 oz ≈ 28.3495 grams
        assert Decimal(28) < result < Decimal(29)

    async def test_pounds_to_grams(self, converter: UnitConverter) -> None:
        """Should convert pounds to grams."""
        quantity = Quantity(amount=1, measurement=IngredientUnit.LB)
        result = await converter.to_grams(quantity, "meat")
        # 1 lb ≈ 453.592 grams
        assert Decimal(453) < result < Decimal(454)

    async def test_fractional_weight(self, converter: UnitConverter) -> None:
        """Should handle fractional weights."""
        quantity = Quantity(amount=0.5, measurement=IngredientUnit.KG)
        result = await converter.to_grams(quantity, "sugar")
        assert result == Decimal(500)


class TestVolumeConversionsWithFallback:
    """Tests for volume conversions using fallback (water density)."""

    async def test_ml_to_grams_fallback(self, converter: UnitConverter) -> None:
        """Should convert ml using 1 g/ml fallback."""
        quantity = Quantity(amount=100, measurement=IngredientUnit.ML)
        result = await converter.to_grams(quantity, "unknown liquid")
        # Fallback: 1 g/ml
        assert result == Decimal(100)

    async def test_liters_to_grams_fallback(self, converter: UnitConverter) -> None:
        """Should convert liters using fallback."""
        quantity = Quantity(amount=1, measurement=IngredientUnit.L)
        result = await converter.to_grams(quantity, "water")
        # 1 L = 1000 ml * 1 g/ml = 1000g
        assert result == Decimal(1000)

    async def test_cup_to_grams_fallback(self, converter: UnitConverter) -> None:
        """Should convert cups using fallback."""
        quantity = Quantity(amount=1, measurement=IngredientUnit.CUP)
        result = await converter.to_grams(quantity, "unknown")
        # 1 cup ≈ 236.588 ml * 1 g/ml
        assert Decimal(236) < result < Decimal(237)

    async def test_tablespoon_to_grams_fallback(self, converter: UnitConverter) -> None:
        """Should convert tablespoons using fallback."""
        quantity = Quantity(amount=1, measurement=IngredientUnit.TBSP)
        result = await converter.to_grams(quantity, "oil")
        # 1 tbsp ≈ 14.787 ml * 1 g/ml
        assert Decimal(14) < result < Decimal(15)

    async def test_teaspoon_to_grams_fallback(self, converter: UnitConverter) -> None:
        """Should convert teaspoons using fallback."""
        quantity = Quantity(amount=1, measurement=IngredientUnit.TSP)
        result = await converter.to_grams(quantity, "salt")
        # 1 tsp ≈ 4.929 ml * 1 g/ml
        assert Decimal(4) < result < Decimal(5)


class TestVolumeConversionsWithDatabase:
    """Tests for volume conversions with database lookups."""

    async def test_uses_database_portion_weight(
        self,
        converter_with_repo: UnitConverter,
        mock_repository: MagicMock,
    ) -> None:
        """Should use database portion weight when available."""
        # 1 cup flour = 125g from database
        mock_repository.get_portion_weight.return_value = Decimal(125)

        quantity = Quantity(amount=2, measurement=IngredientUnit.CUP)
        result = await converter_with_repo.to_grams(quantity, "flour")

        assert result == Decimal(250)  # 2 * 125g
        mock_repository.get_portion_weight.assert_called_once_with(
            ingredient_name="flour",
            unit="CUP",
        )

    async def test_falls_back_when_not_in_database(
        self,
        converter_with_repo: UnitConverter,
        mock_repository: MagicMock,
    ) -> None:
        """Should fall back to Pint conversion when not in database."""
        mock_repository.get_portion_weight.return_value = None

        quantity = Quantity(amount=1, measurement=IngredientUnit.CUP)
        result = await converter_with_repo.to_grams(quantity, "unknown")

        # Falls back to ml * 1 g/ml
        assert Decimal(236) < result < Decimal(237)


class TestCountConversionsWithFallback:
    """Tests for count unit conversions using fallback."""

    async def test_piece_fallback(self, converter: UnitConverter) -> None:
        """Should use 100g fallback for piece."""
        quantity = Quantity(amount=1, measurement=IngredientUnit.PIECE)
        result = await converter.to_grams(quantity, "unknown item")
        assert result == Decimal(100)

    async def test_multiple_pieces_fallback(self, converter: UnitConverter) -> None:
        """Should multiply fallback by amount."""
        quantity = Quantity(amount=3, measurement=IngredientUnit.PIECE)
        result = await converter.to_grams(quantity, "unknown item")
        assert result == Decimal(300)

    async def test_clove_fallback(self, converter: UnitConverter) -> None:
        """Should use 100g fallback for clove."""
        quantity = Quantity(amount=2, measurement=IngredientUnit.CLOVE)
        result = await converter.to_grams(quantity, "garlic")
        assert result == Decimal(200)


class TestCountConversionsWithDatabase:
    """Tests for count unit conversions with database lookups."""

    async def test_uses_database_portion_weight(
        self,
        converter_with_repo: UnitConverter,
        mock_repository: MagicMock,
    ) -> None:
        """Should use database portion weight for count units."""
        # 1 medium apple = 182g from database
        mock_repository.get_portion_weight.return_value = Decimal(182)

        quantity = Quantity(amount=2, measurement=IngredientUnit.PIECE)
        result = await converter_with_repo.to_grams(quantity, "apple")

        assert result == Decimal(364)  # 2 * 182g
        mock_repository.get_portion_weight.assert_called_once()

    async def test_garlic_clove_from_database(
        self,
        converter_with_repo: UnitConverter,
        mock_repository: MagicMock,
    ) -> None:
        """Should look up clove weight from database."""
        mock_repository.get_portion_weight.return_value = Decimal(3)

        quantity = Quantity(amount=4, measurement=IngredientUnit.CLOVE)
        result = await converter_with_repo.to_grams(quantity, "garlic")

        assert result == Decimal(12)  # 4 * 3g


class TestUnitTypeChecks:
    """Tests for unit type classification methods."""

    def test_is_weight_unit(self, converter: UnitConverter) -> None:
        """Should identify weight units correctly."""
        assert converter.is_weight_unit(IngredientUnit.G) is True
        assert converter.is_weight_unit(IngredientUnit.KG) is True
        assert converter.is_weight_unit(IngredientUnit.OZ) is True
        assert converter.is_weight_unit(IngredientUnit.LB) is True
        assert converter.is_weight_unit(IngredientUnit.CUP) is False
        assert converter.is_weight_unit(IngredientUnit.PIECE) is False

    def test_is_volume_unit(self, converter: UnitConverter) -> None:
        """Should identify volume units correctly."""
        assert converter.is_volume_unit(IngredientUnit.ML) is True
        assert converter.is_volume_unit(IngredientUnit.L) is True
        assert converter.is_volume_unit(IngredientUnit.CUP) is True
        assert converter.is_volume_unit(IngredientUnit.TBSP) is True
        assert converter.is_volume_unit(IngredientUnit.TSP) is True
        assert converter.is_volume_unit(IngredientUnit.G) is False
        assert converter.is_volume_unit(IngredientUnit.PIECE) is False

    def test_is_count_unit(self, converter: UnitConverter) -> None:
        """Should identify count units correctly."""
        assert converter.is_count_unit(IngredientUnit.PIECE) is True
        assert converter.is_count_unit(IngredientUnit.CLOVE) is True
        assert converter.is_count_unit(IngredientUnit.SLICE) is True
        assert converter.is_count_unit(IngredientUnit.G) is False
        assert converter.is_count_unit(IngredientUnit.CUP) is False


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    async def test_zero_amount(self, converter: UnitConverter) -> None:
        """Should handle zero amount."""
        quantity = Quantity(amount=0, measurement=IngredientUnit.G)
        result = await converter.to_grams(quantity, "flour")
        assert result == Decimal(0)

    async def test_small_fractional_amount(self, converter: UnitConverter) -> None:
        """Should handle small fractional amounts."""
        quantity = Quantity(amount=0.25, measurement=IngredientUnit.TSP)
        result = await converter.to_grams(quantity, "salt")
        assert result > Decimal(0)
        assert result < Decimal(2)

    async def test_ingredient_name_normalized(
        self,
        converter_with_repo: UnitConverter,
        mock_repository: MagicMock,
    ) -> None:
        """Should normalize ingredient name for lookup."""
        mock_repository.get_portion_weight.return_value = Decimal(125)

        quantity = Quantity(amount=1, measurement=IngredientUnit.CUP)
        await converter_with_repo.to_grams(quantity, "  FLOUR  ")

        # Should be lowercased and stripped
        mock_repository.get_portion_weight.assert_called_once_with(
            ingredient_name="flour",
            unit="CUP",
        )
