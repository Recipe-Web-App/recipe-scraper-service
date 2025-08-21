"""Unit tests for the RecipeStep model."""

from datetime import datetime

import pytest

from app.db.models.recipe_models.recipe_step import RecipeStep


class TestRecipeStep:
    """Test cases for RecipeStep model."""

    @pytest.mark.unit
    def test_recipe_step_model_creation(self, mock_datetime: datetime) -> None:
        """Test creating a RecipeStep instance with all fields."""
        recipe_step = RecipeStep(
            step_id=1,
            recipe_id=1,
            step_number=1,
            instruction="Preheat the oven to 350°F (175°C).",
            optional=False,
            timer_seconds=300,
            created_at=mock_datetime,
        )

        assert recipe_step.step_id == 1
        assert recipe_step.recipe_id == 1
        assert recipe_step.step_number == 1
        assert recipe_step.instruction == "Preheat the oven to 350°F (175°C)."
        assert recipe_step.optional is False
        assert recipe_step.timer_seconds == 300
        assert recipe_step.created_at == mock_datetime

    @pytest.mark.unit
    def test_recipe_step_model_creation_minimal(self) -> None:
        """Test creating a RecipeStep instance with minimal required fields."""
        recipe_step = RecipeStep(
            recipe_id=1,
            step_number=1,
            instruction="Mix ingredients together.",
        )

        assert recipe_step.recipe_id == 1
        assert recipe_step.step_number == 1
        assert recipe_step.instruction == "Mix ingredients together."
        # Default value depends on server default, so could be None initially
        assert recipe_step.optional in (False, None)
        assert recipe_step.timer_seconds is None

    @pytest.mark.unit
    def test_recipe_step_model_with_optional_flag(self) -> None:
        """Test creating a RecipeStep instance with optional=True."""
        recipe_step = RecipeStep(
            recipe_id=1,
            step_number=2,
            instruction="Optional: Garnish with fresh herbs.",
            optional=True,
        )

        assert recipe_step.recipe_id == 1
        assert recipe_step.step_number == 2
        assert recipe_step.instruction == "Optional: Garnish with fresh herbs."
        assert recipe_step.optional is True

    @pytest.mark.unit
    def test_recipe_step_model_with_various_step_numbers(self) -> None:
        """Test creating RecipeStep instances with different step numbers."""
        step_numbers_to_test = [1, 5, 10, 25, 100]

        for step_number in step_numbers_to_test:
            recipe_step = RecipeStep(
                recipe_id=1,
                step_number=step_number,
                instruction=f"Step {step_number} instruction.",
            )
            assert recipe_step.step_number == step_number

    @pytest.mark.unit
    def test_recipe_step_model_with_various_timer_values(self) -> None:
        """Test creating RecipeStep instances with different timer values."""
        timer_values_to_test = [
            30,  # 30 seconds
            60,  # 1 minute
            300,  # 5 minutes
            1800,  # 30 minutes
            3600,  # 1 hour
            7200,  # 2 hours
        ]

        for timer_seconds in timer_values_to_test:
            recipe_step = RecipeStep(
                recipe_id=1,
                step_number=1,
                instruction="Timed step instruction.",
                timer_seconds=timer_seconds,
            )
            assert recipe_step.timer_seconds == timer_seconds

    @pytest.mark.unit
    def test_recipe_step_model_with_none_timer(self) -> None:
        """Test creating RecipeStep with None timer value."""
        recipe_step = RecipeStep(
            recipe_id=1,
            step_number=1,
            instruction="Step with no timer.",
            timer_seconds=None,
        )

        assert recipe_step.timer_seconds is None

    @pytest.mark.unit
    def test_recipe_step_model_with_zero_timer(self) -> None:
        """Test creating RecipeStep with zero timer value."""
        recipe_step = RecipeStep(
            recipe_id=1,
            step_number=1,
            instruction="Immediate step.",
            timer_seconds=0,
        )

        assert recipe_step.timer_seconds == 0

    @pytest.mark.unit
    def test_recipe_step_model_tablename(self) -> None:
        """Test that the table name is correctly set."""
        recipe_step = RecipeStep(
            recipe_id=1,
            step_number=1,
            instruction="Test step",
        )
        assert recipe_step.__tablename__ == "recipe_steps"

    @pytest.mark.unit
    def test_recipe_step_model_table_args(self) -> None:
        """Test that the table args schema is correctly set."""
        recipe_step = RecipeStep(
            recipe_id=1,
            step_number=1,
            instruction="Test step",
        )
        assert recipe_step.__table_args__ == ({"schema": "recipe_manager"},)

    @pytest.mark.unit
    def test_recipe_step_model_inheritance(self) -> None:
        """Test that RecipeStep inherits from BaseDatabaseModel."""
        from app.db.models.base_database_model import BaseDatabaseModel

        recipe_step = RecipeStep(
            recipe_id=1,
            step_number=1,
            instruction="Test step",
        )
        assert isinstance(recipe_step, BaseDatabaseModel)

    @pytest.mark.unit
    def test_recipe_step_model_serialization(self, mock_datetime: datetime) -> None:
        """Test that RecipeStep can be serialized to JSON."""
        recipe_step = RecipeStep(
            step_id=1,
            recipe_id=1,
            step_number=3,
            instruction="Bake for 25 minutes until golden brown.",
            optional=False,
            timer_seconds=1500,
            created_at=mock_datetime,
        )

        json_str = recipe_step._to_json()

        # Should contain all the expected fields
        assert '"step_id": 1' in json_str
        assert '"recipe_id": 1' in json_str
        assert '"step_number": 3' in json_str
        assert '"instruction": "Bake for 25 minutes until golden brown."' in json_str
        assert '"optional": false' in json_str
        assert '"timer_seconds": 1500' in json_str

    @pytest.mark.unit
    def test_recipe_step_model_string_representation(self) -> None:
        """Test string representation of RecipeStep model."""
        recipe_step = RecipeStep(
            step_id=1,
            recipe_id=1,
            step_number=1,
            instruction="String test step.",
        )

        str_repr = str(recipe_step)

        # Should be a JSON string representation
        assert '"step_id": 1' in str_repr
        assert '"instruction": "String test step."' in str_repr

    @pytest.mark.unit
    def test_recipe_step_model_relationships(self) -> None:
        """Test that the relationships are properly configured."""
        recipe_step = RecipeStep(
            recipe_id=1,
            step_number=1,
            instruction="Relationship test step",
        )

        # Recipe relationship should be configured but initially None
        assert hasattr(recipe_step, 'recipe')

    @pytest.mark.unit
    def test_recipe_step_model_with_long_instruction(self) -> None:
        """Test creating a RecipeStep with a long instruction."""
        long_instruction = "This is a very detailed cooking instruction. " * 50
        recipe_step = RecipeStep(
            recipe_id=1,
            step_number=1,
            instruction=long_instruction,
        )

        assert recipe_step.instruction == long_instruction

    @pytest.mark.unit
    def test_recipe_step_model_with_special_characters(self) -> None:
        """Test creating RecipeStep with special characters in instruction."""
        special_instruction = (
            "Mix ingredients: 2½ cups flour, ¼ tsp salt, "
            "1 tbsp sugar @ 350°F for 20-25 mins. "
            "Add spices: cinnamon & nutmeg (optional). "
            "Serve with café au lait! 🍰"
        )

        recipe_step = RecipeStep(
            recipe_id=1,
            step_number=1,
            instruction=special_instruction,
        )

        assert recipe_step.instruction == special_instruction
        assert "½" in recipe_step.instruction
        assert "°F" in recipe_step.instruction
        assert "&" in recipe_step.instruction
        assert "🍰" in recipe_step.instruction

    @pytest.mark.unit
    def test_recipe_step_model_with_different_recipe_ids(self) -> None:
        """Test creating RecipeStep instances for different recipes."""
        recipe_ids_to_test = [1, 5, 100, 9999]

        for recipe_id in recipe_ids_to_test:
            recipe_step = RecipeStep(
                recipe_id=recipe_id,
                step_number=1,
                instruction=f"Step for recipe {recipe_id}.",
            )
            assert recipe_step.recipe_id == recipe_id

    @pytest.mark.unit
    def test_recipe_step_model_with_large_timer_values(self) -> None:
        """Test creating RecipeStep with large timer values."""
        # Test overnight cooking (8 hours)
        overnight_seconds = 8 * 60 * 60  # 28800 seconds

        recipe_step = RecipeStep(
            recipe_id=1,
            step_number=1,
            instruction="Slow cook overnight for 8 hours.",
            timer_seconds=overnight_seconds,
        )

        assert recipe_step.timer_seconds == overnight_seconds

    @pytest.mark.unit
    def test_recipe_step_model_ordering_by_step_number(self) -> None:
        """Test that step numbers can be used for ordering."""
        steps = []

        # Create steps in non-sequential order
        for step_number in [3, 1, 5, 2, 4]:
            step = RecipeStep(
                recipe_id=1,
                step_number=step_number,
                instruction=f"Step {step_number}",
            )
            steps.append(step)

        # Sort by step number
        sorted_steps = sorted(steps, key=lambda s: s.step_number)

        # Verify they are in correct order
        for i, step in enumerate(sorted_steps, 1):
            assert step.step_number == i
