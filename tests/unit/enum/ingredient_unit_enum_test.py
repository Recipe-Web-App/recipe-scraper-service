"""Unit tests for the IngredientUnitEnum."""

import pytest

from app.enums.ingredient_unit_enum import IngredientUnitEnum


class TestIngredientUnitEnum:
    """Unit tests for the IngredientUnitEnum class."""

    @pytest.mark.unit
    def test_ingredient_unit_enum_is_string_enum(self) -> None:
        """Test that IngredientUnitEnum values are strings."""
        # Act & Assert
        assert isinstance(IngredientUnitEnum.G, str)
        assert isinstance(IngredientUnitEnum.CUP, str)
        assert isinstance(IngredientUnitEnum.TBSP, str)

    @pytest.mark.unit
    def test_ingredient_unit_enum_values(self) -> None:
        """Test that all ingredient unit enum values are correct."""
        # Test all ingredient unit values using a dictionary mapping
        expected_values = {
            # Weight units
            IngredientUnitEnum.G: "G",
            IngredientUnitEnum.KG: "KG",
            IngredientUnitEnum.OZ: "OZ",
            IngredientUnitEnum.LB: "LB",
            # Volume units
            IngredientUnitEnum.ML: "ML",
            IngredientUnitEnum.L: "L",
            IngredientUnitEnum.CUP: "CUP",
            IngredientUnitEnum.TBSP: "TBSP",
            IngredientUnitEnum.TSP: "TSP",
            # Count units
            IngredientUnitEnum.PIECE: "PIECE",
            IngredientUnitEnum.CLOVE: "CLOVE",
            IngredientUnitEnum.SLICE: "SLICE",
            IngredientUnitEnum.PINCH: "PINCH",
            # Container units
            IngredientUnitEnum.CAN: "CAN",
            IngredientUnitEnum.BOTTLE: "BOTTLE",
            IngredientUnitEnum.PACKET: "PACKET",
            # Generic unit
            IngredientUnitEnum.UNIT: "UNIT",
        }

        # Assert all values match expected strings
        for enum_val, expected_str in expected_values.items():
            assert enum_val == expected_str

    @pytest.mark.unit
    def test_ingredient_unit_enum_membership(self) -> None:
        """Test that values are members of the enum."""
        # Act & Assert
        assert IngredientUnitEnum.G in IngredientUnitEnum
        assert IngredientUnitEnum.CUP in IngredientUnitEnum
        assert IngredientUnitEnum.TBSP in IngredientUnitEnum
        assert IngredientUnitEnum.PIECE in IngredientUnitEnum
        assert IngredientUnitEnum.UNIT in IngredientUnitEnum

    @pytest.mark.unit
    def test_ingredient_unit_enum_iteration(self) -> None:
        """Test that we can iterate over all ingredient unit values."""
        # Act
        all_units = list(IngredientUnitEnum)

        # Assert
        assert len(all_units) > 0
        assert IngredientUnitEnum.G in all_units
        assert IngredientUnitEnum.CUP in all_units
        assert IngredientUnitEnum.TBSP in all_units
        assert IngredientUnitEnum.UNIT in all_units

    @pytest.mark.unit
    def test_ingredient_unit_enum_count(self) -> None:
        """Test the total count of ingredient unit enums."""
        # Act
        unit_count = len(list(IngredientUnitEnum))

        # Assert - Should have 17 units based on the enum definition
        assert unit_count == 17

    @pytest.mark.unit
    def test_ingredient_unit_enum_string_comparison(self) -> None:
        """Test that enum values can be compared with strings."""
        # Test equality comparisons
        equality_tests = {
            IngredientUnitEnum.G: "G",
            IngredientUnitEnum.CUP: "CUP",
            IngredientUnitEnum.TBSP: "TBSP",
        }

        for enum_val, expected_str in equality_tests.items():
            assert enum_val == expected_str

        # Test inequality with dynamic comparison
        test_cases = [
            (IngredientUnitEnum.G, "KG"),
            (IngredientUnitEnum.CUP, "TBSP"),
        ]

        for enum_val, different_str in test_cases:
            assert enum_val != different_str

    @pytest.mark.unit
    def test_ingredient_unit_enum_uniqueness(self) -> None:
        """Test that all ingredient unit values are unique."""
        # Act
        all_values = [unit.value for unit in IngredientUnitEnum]

        # Assert
        assert len(all_values) == len(set(all_values))

    @pytest.mark.unit
    def test_from_string_with_exact_matches(self) -> None:
        """Test from_string with exact enum value matches."""
        # Act & Assert
        assert IngredientUnitEnum.from_string("G") == IngredientUnitEnum.G
        assert IngredientUnitEnum.from_string("CUP") == IngredientUnitEnum.CUP
        assert IngredientUnitEnum.from_string("TBSP") == IngredientUnitEnum.TBSP

    @pytest.mark.unit
    def test_from_string_with_normalized_values(self) -> None:
        """Test from_string with values that need normalization."""
        # Act & Assert - Test lowercase variations
        assert IngredientUnitEnum.from_string("g") == IngredientUnitEnum.G
        assert IngredientUnitEnum.from_string("cup") == IngredientUnitEnum.CUP
        assert IngredientUnitEnum.from_string("tbsp") == IngredientUnitEnum.TBSP

        # Test long form variations
        assert IngredientUnitEnum.from_string("grams") == IngredientUnitEnum.G
        assert IngredientUnitEnum.from_string("cups") == IngredientUnitEnum.CUP
        assert IngredientUnitEnum.from_string("tablespoons") == IngredientUnitEnum.TBSP

    @pytest.mark.unit
    def test_from_string_with_empty_or_none_input(self) -> None:
        """Test from_string with empty or None input."""
        # Act & Assert
        assert IngredientUnitEnum.from_string("") is None
        assert IngredientUnitEnum.from_string(None) is None  # type: ignore[arg-type]

    @pytest.mark.unit
    def test_from_string_with_invalid_input(self) -> None:
        """Test from_string with invalid input."""
        # Act & Assert
        assert IngredientUnitEnum.from_string("invalid_unit") is None
        assert IngredientUnitEnum.from_string("xyz") is None

    @pytest.mark.unit
    def test_find_unit_in_text_with_valid_units(self) -> None:
        """Test find_unit_in_text with text containing valid units."""
        # Act & Assert
        test_cases = [
            ("2 cups flour", IngredientUnitEnum.CUP),
            ("1 tablespoon oil", IngredientUnitEnum.TBSP),
            ("500 grams sugar", IngredientUnitEnum.G),
            ("1 pound butter", IngredientUnitEnum.LB),
        ]

        for text, expected_unit in test_cases:
            assert IngredientUnitEnum.find_unit_in_text(text) == expected_unit

    @pytest.mark.unit
    def test_find_unit_in_text_with_no_units(self) -> None:
        """Test find_unit_in_text with text containing no recognizable units."""
        # Act & Assert
        test_cases = [
            "some random text",
            "no measurement here",
        ]

        for text in test_cases:
            assert IngredientUnitEnum.find_unit_in_text(text) == IngredientUnitEnum.UNIT

    @pytest.mark.unit
    def test_find_unit_in_text_with_empty_input(self) -> None:
        """Test find_unit_in_text with empty input."""
        # Act & Assert
        assert IngredientUnitEnum.find_unit_in_text("") == IngredientUnitEnum.UNIT
        assert IngredientUnitEnum.find_unit_in_text(None) == IngredientUnitEnum.UNIT  # type: ignore[arg-type]

    @pytest.mark.unit
    def test_find_unit_in_text_prioritizes_longer_matches(self) -> None:
        """Test that find_unit_in_text prioritizes longer, more specific matches."""
        # Act & Assert - "tablespoons" should match before "tbsp" or shorter patterns
        test_cases = [
            ("2 tablespoons", IngredientUnitEnum.TBSP),
            ("1 teaspoon", IngredientUnitEnum.TSP),
        ]

        for text, expected_unit in test_cases:
            assert IngredientUnitEnum.find_unit_in_text(text) == expected_unit

    @pytest.mark.unit
    def test_weight_units_group(self) -> None:
        """Test weight unit grouping."""
        weight_units = {
            IngredientUnitEnum.G,
            IngredientUnitEnum.KG,
            IngredientUnitEnum.OZ,
            IngredientUnitEnum.LB,
        }

        # Act & Assert
        assert len(weight_units) == 4
        for unit in weight_units:
            assert unit in IngredientUnitEnum

    @pytest.mark.unit
    def test_volume_units_group(self) -> None:
        """Test volume unit grouping."""
        volume_units = {
            IngredientUnitEnum.ML,
            IngredientUnitEnum.L,
            IngredientUnitEnum.CUP,
            IngredientUnitEnum.TBSP,
            IngredientUnitEnum.TSP,
        }

        # Act & Assert
        assert len(volume_units) == 5
        for unit in volume_units:
            assert unit in IngredientUnitEnum

    @pytest.mark.unit
    def test_count_units_group(self) -> None:
        """Test count unit grouping."""
        count_units = {
            IngredientUnitEnum.PIECE,
            IngredientUnitEnum.CLOVE,
            IngredientUnitEnum.SLICE,
            IngredientUnitEnum.PINCH,
        }

        # Act & Assert
        assert len(count_units) == 4
        for unit in count_units:
            assert unit in IngredientUnitEnum

    @pytest.mark.unit
    def test_container_units_group(self) -> None:
        """Test container unit grouping."""
        container_units = {
            IngredientUnitEnum.CAN,
            IngredientUnitEnum.BOTTLE,
            IngredientUnitEnum.PACKET,
        }

        # Act & Assert
        assert len(container_units) == 3
        for unit in container_units:
            assert unit in IngredientUnitEnum

    @pytest.mark.unit
    def test_ingredient_unit_enum_can_be_used_in_sets(self) -> None:
        """Test that ingredient unit enums can be used in sets."""
        # Act
        metric_units = {
            IngredientUnitEnum.G,
            IngredientUnitEnum.KG,
            IngredientUnitEnum.ML,
            IngredientUnitEnum.L,
        }
        imperial_units = {
            IngredientUnitEnum.OZ,
            IngredientUnitEnum.LB,
            IngredientUnitEnum.CUP,
            IngredientUnitEnum.TBSP,
            IngredientUnitEnum.TSP,
        }

        # Assert
        assert len(metric_units) == 4
        assert len(imperial_units) == 5
        assert IngredientUnitEnum.G in metric_units
        assert IngredientUnitEnum.CUP in imperial_units
        assert IngredientUnitEnum.G not in imperial_units
        assert IngredientUnitEnum.CUP not in metric_units

    @pytest.mark.unit
    def test_ingredient_unit_enum_serializable_to_string(self) -> None:
        """Test that ingredient unit enums are serializable to strings."""
        # Act & Assert - Test the value attribute for string representation
        assert IngredientUnitEnum.G.value == "G"
        assert IngredientUnitEnum.CUP.value == "CUP"
        assert IngredientUnitEnum.TBSP.value == "TBSP"

    @pytest.mark.unit
    def test_ingredient_unit_enum_name_attribute(self) -> None:
        """Test that ingredient unit enums have correct name attributes."""
        # Act & Assert
        assert IngredientUnitEnum.G.name == "G"
        assert IngredientUnitEnum.KG.name == "KG"
        assert IngredientUnitEnum.CUP.name == "CUP"
        assert IngredientUnitEnum.TBSP.name == "TBSP"

    @pytest.mark.unit
    def test_ingredient_unit_enum_value_attribute(self) -> None:
        """Test that ingredient unit enums have correct value attributes."""
        # Act & Assert
        assert IngredientUnitEnum.G.value == "G"
        assert IngredientUnitEnum.KG.value == "KG"
        assert IngredientUnitEnum.CUP.value == "CUP"
        assert IngredientUnitEnum.TBSP.value == "TBSP"
        assert IngredientUnitEnum.UNIT.value == "UNIT"
