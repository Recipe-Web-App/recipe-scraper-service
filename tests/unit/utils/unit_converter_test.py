"""Unit tests for the UnitConverter utility class."""

from decimal import Decimal

import pytest

from app.enums.ingredient_unit_enum import IngredientUnitEnum
from app.exceptions.custom_exceptions import IncompatibleUnitsError
from app.utils.unit_converter import UnitConverter


class TestCanConvertBetween:
    """Unit tests for the can_convert_between method."""

    @pytest.mark.unit
    def test_can_convert_between_same_unit(self) -> None:
        """Test that conversion is possible between the same unit."""
        # Act & Assert
        assert UnitConverter.can_convert_between(
            IngredientUnitEnum.G, IngredientUnitEnum.G
        )
        assert UnitConverter.can_convert_between(
            IngredientUnitEnum.ML, IngredientUnitEnum.ML
        )
        assert UnitConverter.can_convert_between(
            IngredientUnitEnum.PIECE, IngredientUnitEnum.PIECE
        )

    @pytest.mark.unit
    def test_can_convert_between_weight_units(self) -> None:
        """Test that conversion is possible between different weight units."""
        # Act & Assert
        assert UnitConverter.can_convert_between(
            IngredientUnitEnum.G, IngredientUnitEnum.KG
        )
        assert UnitConverter.can_convert_between(
            IngredientUnitEnum.KG, IngredientUnitEnum.OZ
        )
        assert UnitConverter.can_convert_between(
            IngredientUnitEnum.OZ, IngredientUnitEnum.LB
        )
        assert UnitConverter.can_convert_between(
            IngredientUnitEnum.LB, IngredientUnitEnum.G
        )

    @pytest.mark.unit
    def test_can_convert_between_volume_units(self) -> None:
        """Test that conversion is possible between different volume units."""
        # Act & Assert
        assert UnitConverter.can_convert_between(
            IngredientUnitEnum.ML, IngredientUnitEnum.L
        )
        assert UnitConverter.can_convert_between(
            IngredientUnitEnum.L, IngredientUnitEnum.CUP
        )
        assert UnitConverter.can_convert_between(
            IngredientUnitEnum.CUP, IngredientUnitEnum.TBSP
        )
        assert UnitConverter.can_convert_between(
            IngredientUnitEnum.TBSP, IngredientUnitEnum.TSP
        )

    @pytest.mark.unit
    def test_cannot_convert_weight_to_volume(self) -> None:
        """Test that conversion is not possible between weight and volume units."""
        # Act & Assert
        assert not UnitConverter.can_convert_between(
            IngredientUnitEnum.G, IngredientUnitEnum.ML
        )
        assert not UnitConverter.can_convert_between(
            IngredientUnitEnum.KG, IngredientUnitEnum.L
        )
        assert not UnitConverter.can_convert_between(
            IngredientUnitEnum.OZ, IngredientUnitEnum.CUP
        )

    @pytest.mark.unit
    def test_cannot_convert_volume_to_weight(self) -> None:
        """Test that conversion is not possible between volume and weight units."""
        # Act & Assert
        assert not UnitConverter.can_convert_between(
            IngredientUnitEnum.ML, IngredientUnitEnum.G
        )
        assert not UnitConverter.can_convert_between(
            IngredientUnitEnum.L, IngredientUnitEnum.KG
        )
        assert not UnitConverter.can_convert_between(
            IngredientUnitEnum.CUP, IngredientUnitEnum.OZ
        )

    @pytest.mark.unit
    def test_cannot_convert_count_to_other_units(self) -> None:
        """Test that count units cannot convert to weight/volume units."""
        # Act & Assert
        assert not UnitConverter.can_convert_between(
            IngredientUnitEnum.PIECE, IngredientUnitEnum.G
        )
        assert not UnitConverter.can_convert_between(
            IngredientUnitEnum.CLOVE, IngredientUnitEnum.ML
        )
        assert not UnitConverter.can_convert_between(
            IngredientUnitEnum.SLICE, IngredientUnitEnum.KG
        )

    @pytest.mark.unit
    def test_cannot_convert_other_units_to_count(self) -> None:
        """Test that weight/volume units cannot convert to count units."""
        # Act & Assert
        assert not UnitConverter.can_convert_between(
            IngredientUnitEnum.G, IngredientUnitEnum.PIECE
        )
        assert not UnitConverter.can_convert_between(
            IngredientUnitEnum.ML, IngredientUnitEnum.CLOVE
        )
        assert not UnitConverter.can_convert_between(
            IngredientUnitEnum.KG, IngredientUnitEnum.SLICE
        )

    @pytest.mark.unit
    def test_cannot_convert_between_different_count_units(self) -> None:
        """Test that different count units cannot convert to each other."""
        # Act & Assert
        assert not UnitConverter.can_convert_between(
            IngredientUnitEnum.PIECE, IngredientUnitEnum.CLOVE
        )
        assert not UnitConverter.can_convert_between(
            IngredientUnitEnum.SLICE, IngredientUnitEnum.PINCH
        )
        assert not UnitConverter.can_convert_between(
            IngredientUnitEnum.CAN, IngredientUnitEnum.BOTTLE
        )


class TestConvertQuantity:
    """Unit tests for the convert_quantity method."""

    @pytest.mark.unit
    def test_convert_quantity_same_unit(self) -> None:
        """Test that converting to the same unit returns the same quantity."""
        # Arrange
        quantity = Decimal("100")

        # Act & Assert
        assert (
            UnitConverter.convert_quantity(
                quantity, IngredientUnitEnum.G, IngredientUnitEnum.G
            )
            == quantity
        )
        assert (
            UnitConverter.convert_quantity(
                quantity, IngredientUnitEnum.ML, IngredientUnitEnum.ML
            )
            == quantity
        )

    @pytest.mark.unit
    def test_convert_grams_to_kilograms(self) -> None:
        """Test converting grams to kilograms."""
        # Arrange
        quantity = Decimal("1000")

        # Act
        result = UnitConverter.convert_quantity(
            quantity, IngredientUnitEnum.G, IngredientUnitEnum.KG
        )

        # Assert
        assert result == Decimal("1")

    @pytest.mark.unit
    def test_convert_kilograms_to_grams(self) -> None:
        """Test converting kilograms to grams."""
        # Arrange
        quantity = Decimal("2.5")

        # Act
        result = UnitConverter.convert_quantity(
            quantity, IngredientUnitEnum.KG, IngredientUnitEnum.G
        )

        # Assert
        assert result == Decimal("2500")

    @pytest.mark.unit
    def test_convert_grams_to_ounces(self) -> None:
        """Test converting grams to ounces."""
        # Arrange
        quantity = Decimal("28.3495")

        # Act
        result = UnitConverter.convert_quantity(
            quantity, IngredientUnitEnum.G, IngredientUnitEnum.OZ
        )

        # Assert
        assert result == Decimal("1")

    @pytest.mark.unit
    def test_convert_pounds_to_grams(self) -> None:
        """Test converting pounds to grams."""
        # Arrange
        quantity = Decimal("1")

        # Act
        result = UnitConverter.convert_quantity(
            quantity, IngredientUnitEnum.LB, IngredientUnitEnum.G
        )

        # Assert
        assert result == Decimal("453.592")

    @pytest.mark.unit
    def test_convert_milliliters_to_liters(self) -> None:
        """Test converting milliliters to liters."""
        # Arrange
        quantity = Decimal("1000")

        # Act
        result = UnitConverter.convert_quantity(
            quantity, IngredientUnitEnum.ML, IngredientUnitEnum.L
        )

        # Assert
        assert result == Decimal("1")

    @pytest.mark.unit
    def test_convert_liters_to_milliliters(self) -> None:
        """Test converting liters to milliliters."""
        # Arrange
        quantity = Decimal("0.5")

        # Act
        result = UnitConverter.convert_quantity(
            quantity, IngredientUnitEnum.L, IngredientUnitEnum.ML
        )

        # Assert
        assert result == Decimal("500")

    @pytest.mark.unit
    def test_convert_cups_to_milliliters(self) -> None:
        """Test converting cups to milliliters."""
        # Arrange
        quantity = Decimal("1")

        # Act
        result = UnitConverter.convert_quantity(
            quantity, IngredientUnitEnum.CUP, IngredientUnitEnum.ML
        )

        # Assert
        assert result == Decimal("236.588")

    @pytest.mark.unit
    def test_convert_tablespoons_to_milliliters(self) -> None:
        """Test converting tablespoons to milliliters."""
        # Arrange
        quantity = Decimal("2")

        # Act
        result = UnitConverter.convert_quantity(
            quantity, IngredientUnitEnum.TBSP, IngredientUnitEnum.ML
        )

        # Assert
        assert result == Decimal("29.5736")

    @pytest.mark.unit
    def test_convert_teaspoons_to_tablespoons(self) -> None:
        """Test converting teaspoons to tablespoons."""
        # Arrange
        quantity = Decimal("3")

        # Act
        result = UnitConverter.convert_quantity(
            quantity, IngredientUnitEnum.TSP, IngredientUnitEnum.TBSP
        )

        # Assert
        # Due to conversion factor precision, check within tolerance
        expected = Decimal("1")
        difference = abs(result - expected)
        assert difference < Decimal("0.001")

    @pytest.mark.unit
    def test_convert_quantity_incompatible_units(self) -> None:
        """Test that converting between incompatible units raises an exception."""
        # Arrange
        quantity = Decimal("100")

        # Act & Assert
        with pytest.raises(IncompatibleUnitsError):
            UnitConverter.convert_quantity(
                quantity, IngredientUnitEnum.G, IngredientUnitEnum.ML
            )

        with pytest.raises(IncompatibleUnitsError):
            UnitConverter.convert_quantity(
                quantity, IngredientUnitEnum.PIECE, IngredientUnitEnum.G
            )

        with pytest.raises(IncompatibleUnitsError):
            UnitConverter.convert_quantity(
                quantity, IngredientUnitEnum.CLOVE, IngredientUnitEnum.SLICE
            )

    @pytest.mark.unit
    def test_convert_quantity_decimal_precision(self) -> None:
        """Test that conversions maintain decimal precision."""
        # Arrange
        quantity = Decimal("123.456")

        # Act
        result = UnitConverter.convert_quantity(
            quantity, IngredientUnitEnum.G, IngredientUnitEnum.KG
        )

        # Assert
        assert result == Decimal("0.123456")

    @pytest.mark.unit
    def test_convert_quantity_zero(self) -> None:
        """Test converting zero quantity."""
        # Arrange
        quantity = Decimal("0")

        # Act
        result = UnitConverter.convert_quantity(
            quantity, IngredientUnitEnum.G, IngredientUnitEnum.KG
        )

        # Assert
        assert result == Decimal("0")


class TestCalculateScaleFactor:
    """Unit tests for the calculate_scale_factor method."""

    @pytest.mark.unit
    def test_calculate_scale_factor_same_units(self) -> None:
        """Test scale factor calculation with same units."""
        # Arrange
        old_quantity = Decimal("100")
        new_quantity = Decimal("200")

        # Act
        result = UnitConverter.calculate_scale_factor(
            old_quantity,
            IngredientUnitEnum.G,
            new_quantity,
            IngredientUnitEnum.G,
        )

        # Assert
        assert result == Decimal("2")

    @pytest.mark.unit
    def test_calculate_scale_factor_different_units(self) -> None:
        """Test scale factor calculation with different compatible units."""
        # Arrange
        old_quantity = Decimal("100")  # 100 grams
        new_quantity = Decimal("1")  # 1 kilogram

        # Act
        result = UnitConverter.calculate_scale_factor(
            old_quantity,
            IngredientUnitEnum.G,
            new_quantity,
            IngredientUnitEnum.KG,
        )

        # Assert
        assert result == Decimal("10")  # 1 kg = 1000g, 1000/100 = 10

    @pytest.mark.unit
    def test_calculate_scale_factor_volume_units(self) -> None:
        """Test scale factor calculation with volume units."""
        # Arrange
        old_quantity = Decimal("100")  # 100 ml
        new_quantity = Decimal("1")  # 1 liter

        # Act
        result = UnitConverter.calculate_scale_factor(
            old_quantity,
            IngredientUnitEnum.ML,
            new_quantity,
            IngredientUnitEnum.L,
        )

        # Assert
        assert result == Decimal("10")  # 1 L = 1000ml, 1000/100 = 10

    @pytest.mark.unit
    def test_calculate_scale_factor_fractional(self) -> None:
        """Test scale factor calculation resulting in a fraction."""
        # Arrange
        old_quantity = Decimal("200")
        new_quantity = Decimal("100")

        # Act
        result = UnitConverter.calculate_scale_factor(
            old_quantity,
            IngredientUnitEnum.G,
            new_quantity,
            IngredientUnitEnum.G,
        )

        # Assert
        assert result == Decimal("0.5")

    @pytest.mark.unit
    def test_calculate_scale_factor_incompatible_units(self) -> None:
        """Test that incompatible units raise an exception."""
        # Arrange
        old_quantity = Decimal("100")
        new_quantity = Decimal("200")

        # Act & Assert
        with pytest.raises(IncompatibleUnitsError):
            UnitConverter.calculate_scale_factor(
                old_quantity,
                IngredientUnitEnum.G,
                new_quantity,
                IngredientUnitEnum.ML,
            )

        with pytest.raises(IncompatibleUnitsError):
            UnitConverter.calculate_scale_factor(
                old_quantity,
                IngredientUnitEnum.PIECE,
                new_quantity,
                IngredientUnitEnum.G,
            )

    @pytest.mark.unit
    def test_calculate_scale_factor_zero_old_quantity(self) -> None:
        """Test scale factor calculation with zero old quantity."""
        # Arrange
        old_quantity = Decimal("0")
        new_quantity = Decimal("100")

        # Act & Assert
        with pytest.raises(ZeroDivisionError):
            UnitConverter.calculate_scale_factor(
                old_quantity,
                IngredientUnitEnum.G,
                new_quantity,
                IngredientUnitEnum.G,
            )

    @pytest.mark.unit
    def test_calculate_scale_factor_zero_new_quantity(self) -> None:
        """Test scale factor calculation with zero new quantity."""
        # Arrange
        old_quantity = Decimal("100")
        new_quantity = Decimal("0")

        # Act
        result = UnitConverter.calculate_scale_factor(
            old_quantity,
            IngredientUnitEnum.G,
            new_quantity,
            IngredientUnitEnum.G,
        )

        # Assert
        assert result == Decimal("0")

    @pytest.mark.unit
    def test_calculate_scale_factor_cups_to_tablespoons(self) -> None:
        """Test scale factor calculation between cups and tablespoons."""
        # Arrange
        old_quantity = Decimal("1")  # 1 cup
        new_quantity = Decimal("8")  # 8 tablespoons (half cup)

        # Act
        result = UnitConverter.calculate_scale_factor(
            old_quantity,
            IngredientUnitEnum.CUP,
            new_quantity,
            IngredientUnitEnum.TBSP,
        )

        # Assert
        # 1 cup = 236.588 ml, 8 tbsp = 8 * 14.7868 = 118.2944 ml
        # Scale factor = 118.2944 / 236.588 = 0.5 (approximately)
        expected = Decimal("0.5")
        difference = abs(result - expected)
        assert difference < Decimal("0.001")

    @pytest.mark.unit
    def test_calculate_scale_factor_precision(self) -> None:
        """Test scale factor calculation maintains decimal precision."""
        # Arrange
        old_quantity = Decimal("123.456")
        new_quantity = Decimal("246.912")

        # Act
        result = UnitConverter.calculate_scale_factor(
            old_quantity,
            IngredientUnitEnum.G,
            new_quantity,
            IngredientUnitEnum.G,
        )

        # Assert
        assert result == Decimal("2")


class TestWeightConversions:
    """Unit tests for weight conversion constants."""

    @pytest.mark.unit
    def test_weight_conversion_constants(self) -> None:
        """Test that weight conversion constants are correct."""
        # Assert
        assert UnitConverter._WEIGHT_CONVERSIONS[IngredientUnitEnum.G] == Decimal(1)
        assert UnitConverter._WEIGHT_CONVERSIONS[IngredientUnitEnum.KG] == Decimal(1000)
        assert UnitConverter._WEIGHT_CONVERSIONS[IngredientUnitEnum.OZ] == Decimal(
            "28.3495"
        )
        assert UnitConverter._WEIGHT_CONVERSIONS[IngredientUnitEnum.LB] == Decimal(
            "453.592"
        )


class TestVolumeConversions:
    """Unit tests for volume conversion constants."""

    @pytest.mark.unit
    def test_volume_conversion_constants(self) -> None:
        """Test that volume conversion constants are correct."""
        # Assert
        assert UnitConverter._VOLUME_CONVERSIONS[IngredientUnitEnum.ML] == Decimal(1)
        assert UnitConverter._VOLUME_CONVERSIONS[IngredientUnitEnum.L] == Decimal(1000)
        assert UnitConverter._VOLUME_CONVERSIONS[IngredientUnitEnum.CUP] == Decimal(
            "236.588"
        )
        assert UnitConverter._VOLUME_CONVERSIONS[IngredientUnitEnum.TBSP] == Decimal(
            "14.7868"
        )
        assert UnitConverter._VOLUME_CONVERSIONS[IngredientUnitEnum.TSP] == Decimal(
            "4.92892"
        )


class TestCountUnits:
    """Unit tests for count unit constants."""

    @pytest.mark.unit
    def test_count_units_constants(self) -> None:
        """Test that count units are correctly defined."""
        # Assert
        expected_count_units = {
            IngredientUnitEnum.PIECE,
            IngredientUnitEnum.CLOVE,
            IngredientUnitEnum.SLICE,
            IngredientUnitEnum.PINCH,
            IngredientUnitEnum.CAN,
            IngredientUnitEnum.BOTTLE,
            IngredientUnitEnum.PACKET,
            IngredientUnitEnum.UNIT,
        }
        assert UnitConverter._COUNT_UNITS == expected_count_units


class TestEdgeCases:
    """Unit tests for edge cases and error conditions."""

    @pytest.mark.unit
    def test_very_small_quantities(self) -> None:
        """Test conversions with very small quantities."""
        # Arrange
        quantity = Decimal("0.001")

        # Act
        result = UnitConverter.convert_quantity(
            quantity, IngredientUnitEnum.KG, IngredientUnitEnum.G
        )

        # Assert
        assert result == Decimal("1")

    @pytest.mark.unit
    def test_very_large_quantities(self) -> None:
        """Test conversions with very large quantities."""
        # Arrange
        quantity = Decimal("1000000")

        # Act
        result = UnitConverter.convert_quantity(
            quantity, IngredientUnitEnum.G, IngredientUnitEnum.KG
        )

        # Assert
        assert result == Decimal("1000")

    @pytest.mark.unit
    def test_round_trip_conversion(self) -> None:
        """Test that converting forth and back yields original value."""
        # Arrange
        original_quantity = Decimal("42.5")

        # Act
        converted = UnitConverter.convert_quantity(
            original_quantity, IngredientUnitEnum.G, IngredientUnitEnum.OZ
        )
        back_converted = UnitConverter.convert_quantity(
            converted, IngredientUnitEnum.OZ, IngredientUnitEnum.G
        )

        # Assert
        # Due to decimal precision, we check if they are very close
        difference = abs(original_quantity - back_converted)
        assert difference < Decimal("0.000001")

    @pytest.mark.unit
    def test_conversion_chain(self) -> None:
        """Test a chain of conversions."""
        # Arrange
        quantity = Decimal("1")

        # Act: Convert 1 kg -> g -> oz -> lb
        step1 = UnitConverter.convert_quantity(
            quantity, IngredientUnitEnum.KG, IngredientUnitEnum.G
        )
        step2 = UnitConverter.convert_quantity(
            step1, IngredientUnitEnum.G, IngredientUnitEnum.OZ
        )
        step3 = UnitConverter.convert_quantity(
            step2, IngredientUnitEnum.OZ, IngredientUnitEnum.LB
        )

        # Assert
        # 1 kg = 1000g, 1000g / 28.3495 = ~35.274 oz, 35.274 oz / 16 = ~2.2046 lb
        expected = Decimal("1000") / Decimal("28.3495") / Decimal("16")
        difference = abs(step3 - expected)
        assert difference < Decimal("0.001")
