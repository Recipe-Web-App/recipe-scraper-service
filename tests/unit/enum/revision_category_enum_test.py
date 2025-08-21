"""Unit tests for the RevisionCategoryEnum."""

import pytest

from app.enums.revision_category_enum import RevisionCategoryEnum


class TestRevisionCategoryEnum:
    """Unit tests for the RevisionCategoryEnum class."""

    @pytest.mark.unit
    def test_revision_category_enum_is_string_enum(self) -> None:
        """Test that RevisionCategoryEnum values are strings."""
        # Act & Assert
        assert isinstance(RevisionCategoryEnum.INGREDIENT, str)
        assert isinstance(RevisionCategoryEnum.STEP, str)

    @pytest.mark.unit
    def test_revision_category_enum_values(self) -> None:
        """Test that all revision category enum values are correct."""
        # Test all revision category values using a dictionary mapping
        expected_values = {
            RevisionCategoryEnum.INGREDIENT: "INGREDIENT",
            RevisionCategoryEnum.STEP: "STEP",
        }

        # Assert all values match expected strings
        for enum_val, expected_str in expected_values.items():
            assert enum_val == expected_str

    @pytest.mark.unit
    def test_revision_category_enum_membership(self) -> None:
        """Test that values are members of the enum."""
        # Act & Assert
        assert RevisionCategoryEnum.INGREDIENT in RevisionCategoryEnum
        assert RevisionCategoryEnum.STEP in RevisionCategoryEnum

    @pytest.mark.unit
    def test_revision_category_enum_iteration(self) -> None:
        """Test that we can iterate over all revision category values."""
        # Act
        all_categories = list(RevisionCategoryEnum)

        # Assert
        assert len(all_categories) == 2
        assert RevisionCategoryEnum.INGREDIENT in all_categories
        assert RevisionCategoryEnum.STEP in all_categories

    @pytest.mark.unit
    def test_revision_category_enum_count(self) -> None:
        """Test the total count of revision category enums."""
        # Act
        category_count = len(list(RevisionCategoryEnum))

        # Assert
        assert category_count == 2

    @pytest.mark.unit
    def test_revision_category_enum_string_comparison(self) -> None:
        """Test that enum values can be compared with strings."""
        # Test equality comparisons
        equality_tests = {
            RevisionCategoryEnum.INGREDIENT: "INGREDIENT",
            RevisionCategoryEnum.STEP: "STEP",
        }

        for enum_val, expected_str in equality_tests.items():
            assert enum_val == expected_str

        # Test inequality with dynamic comparison
        test_cases = [
            (RevisionCategoryEnum.INGREDIENT, "STEP"),
            (RevisionCategoryEnum.STEP, "INGREDIENT"),
        ]

        for enum_val, different_str in test_cases:
            assert enum_val != different_str

    @pytest.mark.unit
    def test_revision_category_enum_uniqueness(self) -> None:
        """Test that all revision category values are unique."""
        # Act
        all_values = [category.value for category in RevisionCategoryEnum]

        # Assert
        assert len(all_values) == len(set(all_values))

    @pytest.mark.unit
    def test_revision_category_enum_covers_recipe_components(self) -> None:
        """Test that revision categories cover the main recipe components."""
        # Act & Assert - Verify we have categories for the main recipe components
        assert RevisionCategoryEnum.INGREDIENT in RevisionCategoryEnum
        assert RevisionCategoryEnum.STEP in RevisionCategoryEnum

        # Verify completeness - these are the primary components of a recipe
        expected_categories = {
            RevisionCategoryEnum.INGREDIENT,
            RevisionCategoryEnum.STEP,
        }
        actual_categories = set(RevisionCategoryEnum)
        assert actual_categories == expected_categories

    @pytest.mark.unit
    def test_revision_category_enum_can_be_used_in_sets(self) -> None:
        """Test that revision category enums can be used in sets."""
        # Act
        all_categories = {
            RevisionCategoryEnum.INGREDIENT,
            RevisionCategoryEnum.STEP,
        }

        # Assert
        assert len(all_categories) == 2
        assert RevisionCategoryEnum.INGREDIENT in all_categories
        assert RevisionCategoryEnum.STEP in all_categories

    @pytest.mark.unit
    def test_revision_category_enum_serializable_to_string(self) -> None:
        """Test that revision category enums are serializable to strings."""
        # Act & Assert - Test the value attribute for string representation
        assert RevisionCategoryEnum.INGREDIENT.value == "INGREDIENT"
        assert RevisionCategoryEnum.STEP.value == "STEP"

    @pytest.mark.unit
    def test_revision_category_enum_name_attribute(self) -> None:
        """Test that revision category enums have correct name attributes."""
        # Act & Assert
        assert RevisionCategoryEnum.INGREDIENT.name == "INGREDIENT"
        assert RevisionCategoryEnum.STEP.name == "STEP"

    @pytest.mark.unit
    def test_revision_category_enum_value_attribute(self) -> None:
        """Test that revision category enums have correct value attributes."""
        # Act & Assert
        assert RevisionCategoryEnum.INGREDIENT.value == "INGREDIENT"
        assert RevisionCategoryEnum.STEP.value == "STEP"
