"""Unit tests for the FoodGroupEnum."""

import pytest

from app.enums.food_group_enum import FoodGroupEnum


class TestFoodGroupEnum:
    """Unit tests for the FoodGroupEnum class."""

    @pytest.mark.unit
    def test_food_group_enum_is_string_enum(self) -> None:
        """Test that FoodGroupEnum values are strings."""
        # Act & Assert
        assert isinstance(FoodGroupEnum.VEGETABLES, str)
        assert isinstance(FoodGroupEnum.FRUITS, str)
        assert isinstance(FoodGroupEnum.UNKNOWN, str)

    @pytest.mark.unit
    def test_food_group_enum_values(self) -> None:
        """Test that all food group enum values are correct."""
        # Test all food group values using a dictionary mapping
        expected_values = {
            # Plant-based whole foods
            FoodGroupEnum.VEGETABLES: "VEGETABLES",
            FoodGroupEnum.FRUITS: "FRUITS",
            FoodGroupEnum.GRAINS: "GRAINS",
            FoodGroupEnum.LEGUMES: "LEGUMES",
            FoodGroupEnum.NUTS_SEEDS: "NUTS_SEEDS",
            # Animal products
            FoodGroupEnum.MEAT: "MEAT",
            FoodGroupEnum.POULTRY: "POULTRY",
            FoodGroupEnum.SEAFOOD: "SEAFOOD",
            FoodGroupEnum.DAIRY: "DAIRY",
            # Processed and manufactured foods
            FoodGroupEnum.BEVERAGES: "BEVERAGES",
            FoodGroupEnum.PROCESSED_FOODS: "PROCESSED_FOODS",
            # Fallback
            FoodGroupEnum.UNKNOWN: "UNKNOWN",
        }

        # Assert all values match expected strings
        for enum_val, expected_str in expected_values.items():
            assert enum_val == expected_str

    @pytest.mark.unit
    def test_food_group_enum_membership(self) -> None:
        """Test that values are members of the enum."""
        # Act & Assert
        assert FoodGroupEnum.VEGETABLES in FoodGroupEnum
        assert FoodGroupEnum.FRUITS in FoodGroupEnum
        assert FoodGroupEnum.MEAT in FoodGroupEnum
        assert FoodGroupEnum.DAIRY in FoodGroupEnum
        assert FoodGroupEnum.UNKNOWN in FoodGroupEnum

    @pytest.mark.unit
    def test_food_group_enum_iteration(self) -> None:
        """Test that we can iterate over all food group values."""
        # Act
        all_food_groups = list(FoodGroupEnum)

        # Assert
        assert len(all_food_groups) > 0
        assert FoodGroupEnum.VEGETABLES in all_food_groups
        assert FoodGroupEnum.FRUITS in all_food_groups
        assert FoodGroupEnum.MEAT in all_food_groups
        assert FoodGroupEnum.UNKNOWN in all_food_groups

    @pytest.mark.unit
    def test_food_group_enum_count(self) -> None:
        """Test the total count of food group enums."""
        # Act
        food_group_count = len(list(FoodGroupEnum))

        # Assert - Should have 12 food groups based on the enum definition
        assert food_group_count == 12

    @pytest.mark.unit
    def test_food_group_enum_string_comparison(self) -> None:
        """Test that enum values can be compared with strings."""
        # Test equality comparisons
        equality_tests = {
            FoodGroupEnum.VEGETABLES: "VEGETABLES",
            FoodGroupEnum.FRUITS: "FRUITS",
            FoodGroupEnum.UNKNOWN: "UNKNOWN",
        }

        for enum_val, expected_str in equality_tests.items():
            assert enum_val == expected_str

        # Test inequality with dynamic comparison
        test_cases = [
            (FoodGroupEnum.VEGETABLES, "FRUITS"),
            (FoodGroupEnum.MEAT, "DAIRY"),
        ]

        for enum_val, different_str in test_cases:
            assert enum_val != different_str

    @pytest.mark.unit
    def test_food_group_enum_uniqueness(self) -> None:
        """Test that all food group values are unique."""
        # Act
        all_values = [group.value for group in FoodGroupEnum]

        # Assert
        assert len(all_values) == len(set(all_values))

    @pytest.mark.unit
    def test_plant_based_food_groups(self) -> None:
        """Test that plant-based food groups are present."""
        plant_based_groups = {
            FoodGroupEnum.VEGETABLES,
            FoodGroupEnum.FRUITS,
            FoodGroupEnum.GRAINS,
            FoodGroupEnum.LEGUMES,
            FoodGroupEnum.NUTS_SEEDS,
        }

        # Act & Assert
        assert len(plant_based_groups) == 5
        for food_group in plant_based_groups:
            assert food_group in FoodGroupEnum

    @pytest.mark.unit
    def test_animal_product_food_groups(self) -> None:
        """Test that animal product food groups are present."""
        animal_product_groups = {
            FoodGroupEnum.MEAT,
            FoodGroupEnum.POULTRY,
            FoodGroupEnum.SEAFOOD,
            FoodGroupEnum.DAIRY,
        }

        # Act & Assert
        assert len(animal_product_groups) == 4
        for food_group in animal_product_groups:
            assert food_group in FoodGroupEnum

    @pytest.mark.unit
    def test_processed_food_groups(self) -> None:
        """Test that processed food groups are present."""
        processed_groups = {
            FoodGroupEnum.BEVERAGES,
            FoodGroupEnum.PROCESSED_FOODS,
        }

        # Act & Assert
        assert len(processed_groups) == 2
        for food_group in processed_groups:
            assert food_group in FoodGroupEnum

    @pytest.mark.unit
    def test_food_group_enum_can_be_used_in_sets(self) -> None:
        """Test that food group enums can be used in sets."""
        # Act
        vegetarian_groups = {
            FoodGroupEnum.VEGETABLES,
            FoodGroupEnum.FRUITS,
            FoodGroupEnum.GRAINS,
            FoodGroupEnum.DAIRY,
        }

        # Assert
        assert len(vegetarian_groups) == 4
        assert FoodGroupEnum.VEGETABLES in vegetarian_groups
        assert FoodGroupEnum.DAIRY in vegetarian_groups
        assert FoodGroupEnum.MEAT not in vegetarian_groups
        assert FoodGroupEnum.POULTRY not in vegetarian_groups

    @pytest.mark.unit
    def test_food_group_enum_serializable_to_string(self) -> None:
        """Test that food group enums are serializable to strings."""
        # Act & Assert - Test the value attribute for string representation
        assert FoodGroupEnum.VEGETABLES.value == "VEGETABLES"
        assert FoodGroupEnum.FRUITS.value == "FRUITS"
        assert FoodGroupEnum.UNKNOWN.value == "UNKNOWN"

    @pytest.mark.unit
    def test_food_group_enum_name_attribute(self) -> None:
        """Test that food group enums have correct name attributes."""
        # Act & Assert
        assert FoodGroupEnum.VEGETABLES.name == "VEGETABLES"
        assert FoodGroupEnum.FRUITS.name == "FRUITS"
        assert FoodGroupEnum.NUTS_SEEDS.name == "NUTS_SEEDS"
        assert FoodGroupEnum.PROCESSED_FOODS.name == "PROCESSED_FOODS"

    @pytest.mark.unit
    def test_food_group_enum_value_attribute(self) -> None:
        """Test that food group enums have correct value attributes."""
        # Act & Assert
        assert FoodGroupEnum.VEGETABLES.value == "VEGETABLES"
        assert FoodGroupEnum.FRUITS.value == "FRUITS"
        assert FoodGroupEnum.MEAT.value == "MEAT"
        assert FoodGroupEnum.DAIRY.value == "DAIRY"
        assert FoodGroupEnum.UNKNOWN.value == "UNKNOWN"
