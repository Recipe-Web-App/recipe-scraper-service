"""Unit tests for the MealPlanRecipe model."""

from datetime import date

import pytest

from app.db.models.meal_plan_models.meal_plan_recipe import MealPlanRecipe
from app.enums.meal_type_enum import MealTypeEnum


class TestMealPlanRecipe:
    """Test cases for MealPlanRecipe model."""

    @pytest.mark.unit
    def test_meal_plan_recipe_model_creation(self) -> None:
        """Test creating a MealPlanRecipe instance with all fields."""
        meal_date = date(2024, 1, 15)

        meal_plan_recipe = MealPlanRecipe(
            meal_plan_id=1,
            recipe_id=2,
            meal_date=meal_date,
            meal_type=MealTypeEnum.BREAKFAST,
        )

        assert meal_plan_recipe.meal_plan_id == 1
        assert meal_plan_recipe.recipe_id == 2
        assert meal_plan_recipe.meal_date == meal_date
        assert meal_plan_recipe.meal_type == MealTypeEnum.BREAKFAST

    @pytest.mark.unit
    def test_meal_plan_recipe_model_with_different_meal_types(self) -> None:
        """Test creating MealPlanRecipe instances with different meal types."""
        meal_types_to_test = [
            MealTypeEnum.BREAKFAST,
            MealTypeEnum.LUNCH,
            MealTypeEnum.DINNER,
            MealTypeEnum.SNACK,
        ]

        meal_date = date(2024, 1, 15)

        for meal_type in meal_types_to_test:
            meal_plan_recipe = MealPlanRecipe(
                meal_plan_id=1,
                recipe_id=2,
                meal_date=meal_date,
                meal_type=meal_type,
            )
            assert meal_plan_recipe.meal_type == meal_type

    @pytest.mark.unit
    def test_meal_plan_recipe_model_with_different_dates(self) -> None:
        """Test creating MealPlanRecipe instances with different dates."""
        dates_to_test = [
            date(2024, 1, 1),  # New Year's Day
            date(2024, 2, 29),  # Leap year
            date(2024, 12, 31),  # New Year's Eve
            date(2025, 6, 15),  # Future date
            date(2020, 3, 10),  # Past date
        ]

        for meal_date in dates_to_test:
            meal_plan_recipe = MealPlanRecipe(
                meal_plan_id=1,
                recipe_id=2,
                meal_date=meal_date,
                meal_type=MealTypeEnum.LUNCH,
            )
            assert meal_plan_recipe.meal_date == meal_date

    @pytest.mark.unit
    def test_meal_plan_recipe_model_with_different_ids(self) -> None:
        """Test creating MealPlanRecipe instances with different ID combinations."""
        id_combinations = [
            (1, 1),
            (1, 100),
            (50, 1),
            (999, 888),
            (1234, 5678),
        ]

        meal_date = date(2024, 1, 15)

        for meal_plan_id, recipe_id in id_combinations:
            meal_plan_recipe = MealPlanRecipe(
                meal_plan_id=meal_plan_id,
                recipe_id=recipe_id,
                meal_date=meal_date,
                meal_type=MealTypeEnum.DINNER,
            )
            assert meal_plan_recipe.meal_plan_id == meal_plan_id
            assert meal_plan_recipe.recipe_id == recipe_id

    @pytest.mark.unit
    def test_meal_plan_recipe_model_tablename(self) -> None:
        """Test that the table name is correctly set."""
        meal_plan_recipe = MealPlanRecipe(
            meal_plan_id=1,
            recipe_id=2,
            meal_date=date(2024, 1, 15),
            meal_type=MealTypeEnum.BREAKFAST,
        )
        assert meal_plan_recipe.__tablename__ == "meal_plan_recipes"

    @pytest.mark.unit
    def test_meal_plan_recipe_model_table_args(self) -> None:
        """Test that the table args schema is correctly set."""
        meal_plan_recipe = MealPlanRecipe(
            meal_plan_id=1,
            recipe_id=2,
            meal_date=date(2024, 1, 15),
            meal_type=MealTypeEnum.BREAKFAST,
        )
        assert meal_plan_recipe.__table_args__ == ({"schema": "recipe_manager"},)

    @pytest.mark.unit
    def test_meal_plan_recipe_model_inheritance(self) -> None:
        """Test that MealPlanRecipe inherits from BaseDatabaseModel."""
        from app.db.models.base_database_model import BaseDatabaseModel

        meal_plan_recipe = MealPlanRecipe(
            meal_plan_id=1,
            recipe_id=2,
            meal_date=date(2024, 1, 15),
            meal_type=MealTypeEnum.BREAKFAST,
        )
        assert isinstance(meal_plan_recipe, BaseDatabaseModel)

    @pytest.mark.unit
    def test_meal_plan_recipe_model_serialization(self) -> None:
        """Test that MealPlanRecipe can be serialized to JSON."""
        meal_date = date(2024, 1, 15)

        meal_plan_recipe = MealPlanRecipe(
            meal_plan_id=1,
            recipe_id=2,
            meal_date=meal_date,
            meal_type=MealTypeEnum.DINNER,
        )

        json_str = meal_plan_recipe._to_json()

        # Should contain all the expected fields
        assert '"meal_plan_id": 1' in json_str
        assert '"recipe_id": 2' in json_str
        assert '"meal_date":' in json_str
        assert '"meal_type": "DINNER"' in json_str  # enum value

    @pytest.mark.unit
    def test_meal_plan_recipe_model_string_representation(self) -> None:
        """Test string representation of MealPlanRecipe model."""
        meal_plan_recipe = MealPlanRecipe(
            meal_plan_id=1,
            recipe_id=2,
            meal_date=date(2024, 1, 15),
            meal_type=MealTypeEnum.LUNCH,
        )

        str_repr = str(meal_plan_recipe)

        # Should be a JSON string representation
        assert '"meal_plan_id": 1' in str_repr
        assert '"recipe_id": 2' in str_repr
        assert '"meal_type": "LUNCH"' in str_repr

    @pytest.mark.unit
    def test_meal_plan_recipe_model_repr(self) -> None:
        """Test repr representation of MealPlanRecipe model."""
        meal_plan_recipe = MealPlanRecipe(
            meal_plan_id=1,
            recipe_id=2,
            meal_date=date(2024, 1, 15),
            meal_type=MealTypeEnum.SNACK,
        )

        repr_str = repr(meal_plan_recipe)

        # Should be a JSON string representation
        assert '"meal_plan_id": 1' in repr_str
        assert '"recipe_id": 2' in repr_str
        assert '"meal_type": "SNACK"' in repr_str

    @pytest.mark.unit
    def test_meal_plan_recipe_model_relationships(self) -> None:
        """Test that the relationships are properly configured."""
        meal_plan_recipe = MealPlanRecipe(
            meal_plan_id=1,
            recipe_id=2,
            meal_date=date(2024, 1, 15),
            meal_type=MealTypeEnum.BREAKFAST,
        )

        # MealPlan relationship should be configured but initially None
        assert hasattr(meal_plan_recipe, 'meal_plan')

    @pytest.mark.unit
    def test_meal_plan_recipe_model_composite_primary_key(self) -> None:
        """Test that MealPlanRecipe uses composite primary key."""
        meal_date = date(2024, 1, 15)

        meal_plan_recipe = MealPlanRecipe(
            meal_plan_id=1,
            recipe_id=2,
            meal_date=meal_date,
            meal_type=MealTypeEnum.BREAKFAST,
        )

        # All three fields should be part of the primary key
        assert meal_plan_recipe.meal_plan_id == 1
        assert meal_plan_recipe.recipe_id == 2
        assert meal_plan_recipe.meal_date == meal_date

    @pytest.mark.unit
    def test_meal_plan_recipe_model_same_recipe_different_meals(self) -> None:
        """Test that same recipe can be used for different meal types on same date."""
        meal_date = date(2024, 1, 15)

        breakfast = MealPlanRecipe(
            meal_plan_id=1,
            recipe_id=100,  # Same recipe
            meal_date=meal_date,
            meal_type=MealTypeEnum.BREAKFAST,
        )

        lunch = MealPlanRecipe(
            meal_plan_id=1,
            recipe_id=100,  # Same recipe
            meal_date=meal_date,
            meal_type=MealTypeEnum.LUNCH,
        )

        assert breakfast.recipe_id == lunch.recipe_id
        assert breakfast.meal_date == lunch.meal_date
        assert breakfast.meal_type != lunch.meal_type

    @pytest.mark.unit
    def test_meal_plan_recipe_model_same_recipe_different_dates(self) -> None:
        """Test that same recipe can be used on different dates."""
        date1 = date(2024, 1, 15)
        date2 = date(2024, 1, 16)

        day1_meal = MealPlanRecipe(
            meal_plan_id=1,
            recipe_id=100,  # Same recipe
            meal_date=date1,
            meal_type=MealTypeEnum.DINNER,
        )

        day2_meal = MealPlanRecipe(
            meal_plan_id=1,
            recipe_id=100,  # Same recipe
            meal_date=date2,
            meal_type=MealTypeEnum.DINNER,
        )

        assert day1_meal.recipe_id == day2_meal.recipe_id
        assert day1_meal.meal_type == day2_meal.meal_type
        assert day1_meal.meal_date != day2_meal.meal_date

    @pytest.mark.unit
    def test_meal_plan_recipe_model_weekly_meal_plan(self) -> None:
        """Test creating a week's worth of meal plan recipes."""
        base_date = date(2024, 1, 15)
        meal_plan_id = 1

        weekly_meals = []

        # Create meals for 7 days
        for day_offset in range(7):
            meal_date = date(
                base_date.year, base_date.month, base_date.day + day_offset
            )

            for meal_type in [
                MealTypeEnum.BREAKFAST,
                MealTypeEnum.LUNCH,
                MealTypeEnum.DINNER,
            ]:
                meal = MealPlanRecipe(
                    meal_plan_id=meal_plan_id,
                    recipe_id=day_offset * 3 + list(MealTypeEnum).index(meal_type) + 1,
                    meal_date=meal_date,
                    meal_type=meal_type,
                )
                weekly_meals.append(meal)

        # Should have 21 meals (7 days * 3 meals)
        assert len(weekly_meals) == 21

        # Verify all meals have the same meal plan ID
        for meal in weekly_meals:
            assert meal.meal_plan_id == meal_plan_id

    @pytest.mark.unit
    def test_meal_plan_recipe_model_date_range_boundaries(self) -> None:
        """Test MealPlanRecipe with date range boundaries."""
        boundary_dates = [
            date(1900, 1, 1),  # Early date
            date(2000, 2, 29),  # Leap year Feb 29
            date(2100, 12, 31),  # Future date
        ]

        for meal_date in boundary_dates:
            meal_plan_recipe = MealPlanRecipe(
                meal_plan_id=1,
                recipe_id=2,
                meal_date=meal_date,
                meal_type=MealTypeEnum.LUNCH,
            )
            assert meal_plan_recipe.meal_date == meal_date
