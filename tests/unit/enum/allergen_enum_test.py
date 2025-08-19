"""Unit tests for the AllergenEnum."""

import pytest

from app.enums.allergen_enum import AllergenEnum


class TestAllergenEnum:
    """Unit tests for the AllergenEnum class."""

    @pytest.mark.unit
    def test_allergen_enum_is_string_enum(self) -> None:
        """Test that AllergenEnum values are strings."""
        # Act & Assert
        assert isinstance(AllergenEnum.MILK, str)
        assert isinstance(AllergenEnum.EGGS, str)
        assert isinstance(AllergenEnum.NONE, str)

    @pytest.mark.unit
    def test_allergen_enum_values(self) -> None:
        """Test that all allergen enum values are correct."""
        # Test all allergen values using a dictionary mapping
        expected_values = {
            # FDA Major Allergens (Top 9)
            AllergenEnum.MILK: "MILK",
            AllergenEnum.EGGS: "EGGS",
            AllergenEnum.FISH: "FISH",
            AllergenEnum.SHELLFISH: "SHELLFISH",
            AllergenEnum.TREE_NUTS: "TREE_NUTS",
            AllergenEnum.PEANUTS: "PEANUTS",
            AllergenEnum.WHEAT: "WHEAT",
            AllergenEnum.SOYBEANS: "SOYBEANS",
            AllergenEnum.SESAME: "SESAME",
            # Additional EU Major Allergens
            AllergenEnum.CELERY: "CELERY",
            AllergenEnum.MUSTARD: "MUSTARD",
            AllergenEnum.LUPIN: "LUPIN",
            AllergenEnum.SULPHITES: "SULPHITES",
            # Tree Nut Specifics
            AllergenEnum.ALMONDS: "ALMONDS",
            AllergenEnum.CASHEWS: "CASHEWS",
            AllergenEnum.HAZELNUTS: "HAZELNUTS",
            AllergenEnum.WALNUTS: "WALNUTS",
            # Common Additional Allergens
            AllergenEnum.GLUTEN: "GLUTEN",
            AllergenEnum.COCONUT: "COCONUT",
            AllergenEnum.CORN: "CORN",
            AllergenEnum.YEAST: "YEAST",
            AllergenEnum.GELATIN: "GELATIN",
            AllergenEnum.KIWI: "KIWI",
            # Religious/Dietary
            AllergenEnum.PORK: "PORK",
            AllergenEnum.BEEF: "BEEF",
            AllergenEnum.ALCOHOL: "ALCOHOL",
            # Additives/Chemicals
            AllergenEnum.SULFUR_DIOXIDE: "SULFUR_DIOXIDE",
            AllergenEnum.PHENYLALANINE: "PHENYLALANINE",
            # Other
            AllergenEnum.NONE: "NONE",
            AllergenEnum.UNKNOWN: "UNKNOWN",
        }

        # Assert all values match expected strings
        for enum_val, expected_str in expected_values.items():
            assert enum_val == expected_str

    @pytest.mark.unit
    def test_allergen_enum_membership(self) -> None:
        """Test that values are members of the enum."""
        # Act & Assert
        assert AllergenEnum.MILK in AllergenEnum
        assert AllergenEnum.EGGS in AllergenEnum
        assert AllergenEnum.GLUTEN in AllergenEnum
        assert AllergenEnum.NONE in AllergenEnum
        assert AllergenEnum.UNKNOWN in AllergenEnum

    @pytest.mark.unit
    def test_allergen_enum_iteration(self) -> None:
        """Test that we can iterate over all allergen values."""
        # Act
        all_allergens = list(AllergenEnum)

        # Assert
        assert len(all_allergens) > 0
        assert AllergenEnum.MILK in all_allergens
        assert AllergenEnum.EGGS in all_allergens
        assert AllergenEnum.NONE in all_allergens
        assert AllergenEnum.UNKNOWN in all_allergens

    @pytest.mark.unit
    def test_allergen_enum_count(self) -> None:
        """Test the total count of allergen enums."""
        # Act
        allergen_count = len(list(AllergenEnum))

        # Assert - Should have 30 allergens based on the enum definition
        assert allergen_count == 30

    @pytest.mark.unit
    def test_allergen_enum_string_comparison(self) -> None:
        """Test that enum values can be compared with strings."""
        # Test equality comparisons
        equality_tests = {
            AllergenEnum.MILK: "MILK",
            AllergenEnum.EGGS: "EGGS",
            AllergenEnum.NONE: "NONE",
        }

        for enum_val, expected_str in equality_tests.items():
            assert enum_val == expected_str

        # Test inequality with dynamic comparison
        test_cases = [
            (AllergenEnum.MILK, "EGGS"),
            (AllergenEnum.FISH, "WHEAT"),
        ]

        for enum_val, different_str in test_cases:
            assert enum_val != different_str

    @pytest.mark.unit
    def test_allergen_enum_uniqueness(self) -> None:
        """Test that all allergen values are unique."""
        # Act
        all_values = [allergen.value for allergen in AllergenEnum]

        # Assert
        assert len(all_values) == len(set(all_values))

    @pytest.mark.unit
    def test_fda_major_allergens(self) -> None:
        """Test that FDA major allergens are present."""
        fda_major_allergens = {
            AllergenEnum.MILK,
            AllergenEnum.EGGS,
            AllergenEnum.FISH,
            AllergenEnum.SHELLFISH,
            AllergenEnum.TREE_NUTS,
            AllergenEnum.PEANUTS,
            AllergenEnum.WHEAT,
            AllergenEnum.SOYBEANS,
            AllergenEnum.SESAME,
        }

        # Act & Assert
        assert len(fda_major_allergens) == 9
        for allergen in fda_major_allergens:
            assert allergen in AllergenEnum

    @pytest.mark.unit
    def test_eu_additional_allergens(self) -> None:
        """Test that EU additional allergens are present."""
        eu_additional_allergens = {
            AllergenEnum.CELERY,
            AllergenEnum.MUSTARD,
            AllergenEnum.LUPIN,
            AllergenEnum.SULPHITES,
        }

        # Act & Assert
        assert len(eu_additional_allergens) == 4
        for allergen in eu_additional_allergens:
            assert allergen in AllergenEnum

    @pytest.mark.unit
    def test_tree_nut_specifics(self) -> None:
        """Test that specific tree nut allergens are present."""
        tree_nut_specifics = {
            AllergenEnum.ALMONDS,
            AllergenEnum.CASHEWS,
            AllergenEnum.HAZELNUTS,
            AllergenEnum.WALNUTS,
        }

        # Act & Assert
        assert len(tree_nut_specifics) == 4
        for allergen in tree_nut_specifics:
            assert allergen in AllergenEnum

    @pytest.mark.unit
    def test_religious_dietary_allergens(self) -> None:
        """Test that religious/dietary restriction allergens are present."""
        religious_dietary = {
            AllergenEnum.PORK,
            AllergenEnum.BEEF,
            AllergenEnum.ALCOHOL,
        }

        # Act & Assert
        assert len(religious_dietary) == 3
        for allergen in religious_dietary:
            assert allergen in AllergenEnum

    @pytest.mark.unit
    def test_special_cases(self) -> None:
        """Test special case allergens."""
        # Test special case values
        special_cases = {
            AllergenEnum.NONE: "NONE",
            AllergenEnum.UNKNOWN: "UNKNOWN",
        }

        for enum_val, expected_str in special_cases.items():
            assert enum_val == expected_str
            assert enum_val in AllergenEnum

    @pytest.mark.unit
    def test_allergen_enum_can_be_used_in_sets(self) -> None:
        """Test that allergen enums can be used in sets."""
        # Act
        allergen_set = {
            AllergenEnum.MILK,
            AllergenEnum.EGGS,
            AllergenEnum.PEANUTS,
        }

        # Assert
        assert len(allergen_set) == 3
        assert AllergenEnum.MILK in allergen_set
        assert AllergenEnum.EGGS in allergen_set
        assert AllergenEnum.PEANUTS in allergen_set
        assert AllergenEnum.FISH not in allergen_set

    @pytest.mark.unit
    def test_allergen_enum_serializable_to_string(self) -> None:
        """Test that allergen enums are serializable to strings."""
        # Act & Assert - Test the value attribute for string representation
        assert AllergenEnum.MILK.value == "MILK"
        assert AllergenEnum.EGGS.value == "EGGS"
        assert AllergenEnum.NONE.value == "NONE"

    @pytest.mark.unit
    def test_allergen_enum_name_attribute(self) -> None:
        """Test that allergen enums have correct name attributes."""
        # Act & Assert
        assert AllergenEnum.MILK.name == "MILK"
        assert AllergenEnum.EGGS.name == "EGGS"
        assert AllergenEnum.TREE_NUTS.name == "TREE_NUTS"
        assert AllergenEnum.SULFUR_DIOXIDE.name == "SULFUR_DIOXIDE"
