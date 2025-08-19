"""Unit tests for the MealTypeEnum."""

import pytest

from app.enums.meal_type_enum import MealTypeEnum


class TestMealTypeEnum:
    """Unit tests for the MealTypeEnum class."""

    @pytest.mark.unit
    def test_meal_type_enum_is_string_enum(self) -> None:
        """Test that MealTypeEnum values are strings."""
        # Act & Assert
        assert isinstance(MealTypeEnum.BREAKFAST, str)
        assert isinstance(MealTypeEnum.LUNCH, str)
        assert isinstance(MealTypeEnum.DINNER, str)

    @pytest.mark.unit
    def test_meal_type_enum_values(self) -> None:
        """Test that all meal type enum values are correct."""
        # Test all meal type values using a dictionary mapping
        expected_values = {
            MealTypeEnum.BREAKFAST: "BREAKFAST",
            MealTypeEnum.LUNCH: "LUNCH",
            MealTypeEnum.DINNER: "DINNER",
            MealTypeEnum.SNACK: "SNACK",
            MealTypeEnum.DESSERT: "DESSERT",
        }

        # Assert all values match expected strings
        for enum_val, expected_str in expected_values.items():
            assert enum_val == expected_str

    @pytest.mark.unit
    def test_meal_type_enum_membership(self) -> None:
        """Test that values are members of the enum."""
        # Act & Assert
        assert MealTypeEnum.BREAKFAST in MealTypeEnum
        assert MealTypeEnum.LUNCH in MealTypeEnum
        assert MealTypeEnum.DINNER in MealTypeEnum
        assert MealTypeEnum.SNACK in MealTypeEnum
        assert MealTypeEnum.DESSERT in MealTypeEnum

    @pytest.mark.unit
    def test_meal_type_enum_iteration(self) -> None:
        """Test that we can iterate over all meal type values."""
        # Act
        all_meal_types = list(MealTypeEnum)

        # Assert
        assert len(all_meal_types) == 5
        assert MealTypeEnum.BREAKFAST in all_meal_types
        assert MealTypeEnum.LUNCH in all_meal_types
        assert MealTypeEnum.DINNER in all_meal_types
        assert MealTypeEnum.SNACK in all_meal_types
        assert MealTypeEnum.DESSERT in all_meal_types

    @pytest.mark.unit
    def test_meal_type_enum_count(self) -> None:
        """Test the total count of meal type enums."""
        # Act
        meal_type_count = len(list(MealTypeEnum))

        # Assert
        assert meal_type_count == 5

    @pytest.mark.unit
    def test_meal_type_enum_string_comparison(self) -> None:
        """Test that enum values can be compared with strings."""
        # Test equality comparisons
        equality_tests = {
            MealTypeEnum.BREAKFAST: "BREAKFAST",
            MealTypeEnum.LUNCH: "LUNCH",
            MealTypeEnum.DINNER: "DINNER",
        }

        for enum_val, expected_str in equality_tests.items():
            assert enum_val == expected_str

        # Test inequality with dynamic comparison
        test_cases = [
            (MealTypeEnum.BREAKFAST, "LUNCH"),
            (MealTypeEnum.DINNER, "SNACK"),
        ]

        for enum_val, different_str in test_cases:
            assert enum_val != different_str

    @pytest.mark.unit
    def test_meal_type_enum_uniqueness(self) -> None:
        """Test that all meal type values are unique."""
        # Act
        all_values = [meal_type.value for meal_type in MealTypeEnum]

        # Assert
        assert len(all_values) == len(set(all_values))

    @pytest.mark.unit
    def test_main_meal_types(self) -> None:
        """Test that main meal types are present."""
        main_meals = {
            MealTypeEnum.BREAKFAST,
            MealTypeEnum.LUNCH,
            MealTypeEnum.DINNER,
        }

        # Act & Assert
        assert len(main_meals) == 3
        for meal_type in main_meals:
            assert meal_type in MealTypeEnum

    @pytest.mark.unit
    def test_supplementary_meal_types(self) -> None:
        """Test that supplementary meal types are present."""
        supplementary_meals = {
            MealTypeEnum.SNACK,
            MealTypeEnum.DESSERT,
        }

        # Act & Assert
        assert len(supplementary_meals) == 2
        for meal_type in supplementary_meals:
            assert meal_type in MealTypeEnum

    @pytest.mark.unit
    def test_meal_type_enum_can_be_used_in_sets(self) -> None:
        """Test that meal type enums can be used in sets."""
        # Act
        formal_meals = {
            MealTypeEnum.BREAKFAST,
            MealTypeEnum.LUNCH,
            MealTypeEnum.DINNER,
        }
        casual_meals = {
            MealTypeEnum.SNACK,
            MealTypeEnum.DESSERT,
        }

        # Assert
        assert len(formal_meals) == 3
        assert len(casual_meals) == 2
        assert MealTypeEnum.BREAKFAST in formal_meals
        assert MealTypeEnum.SNACK in casual_meals
        assert MealTypeEnum.SNACK not in formal_meals
        assert MealTypeEnum.DINNER not in casual_meals

    @pytest.mark.unit
    def test_meal_type_enum_serializable_to_string(self) -> None:
        """Test that meal type enums are serializable to strings."""
        # Act & Assert - Test the value attribute for string representation
        assert MealTypeEnum.BREAKFAST.value == "BREAKFAST"
        assert MealTypeEnum.LUNCH.value == "LUNCH"
        assert MealTypeEnum.DINNER.value == "DINNER"

    @pytest.mark.unit
    def test_meal_type_enum_name_attribute(self) -> None:
        """Test that meal type enums have correct name attributes."""
        # Act & Assert
        assert MealTypeEnum.BREAKFAST.name == "BREAKFAST"
        assert MealTypeEnum.LUNCH.name == "LUNCH"
        assert MealTypeEnum.DINNER.name == "DINNER"
        assert MealTypeEnum.SNACK.name == "SNACK"
        assert MealTypeEnum.DESSERT.name == "DESSERT"

    @pytest.mark.unit
    def test_meal_type_enum_value_attribute(self) -> None:
        """Test that meal type enums have correct value attributes."""
        # Act & Assert
        assert MealTypeEnum.BREAKFAST.value == "BREAKFAST"
        assert MealTypeEnum.LUNCH.value == "LUNCH"
        assert MealTypeEnum.DINNER.value == "DINNER"
        assert MealTypeEnum.SNACK.value == "SNACK"
        assert MealTypeEnum.DESSERT.value == "DESSERT"
