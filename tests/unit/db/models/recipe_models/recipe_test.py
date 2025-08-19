"""Unit tests for the Recipe model."""

import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from app.db.models.recipe_models.recipe import Recipe
from app.enums.difficulty_level_enum import DifficultyLevelEnum


class TestRecipe:
    """Test cases for Recipe model."""

    @pytest.mark.unit
    def test_recipe_model_creation(
        self, mock_user_id: uuid.UUID, mock_datetime: datetime
    ) -> None:
        """Test creating a Recipe instance with all fields."""
        recipe = Recipe(
            recipe_id=1,
            user_id=mock_user_id,
            title="Test Recipe",
            description="A test recipe for unit testing",
            origin_url="https://example.com/recipe",
            servings=Decimal("4.0"),
            preparation_time=15,
            cooking_time=30,
            difficulty=DifficultyLevelEnum.EASY,
            created_at=mock_datetime,
            updated_at=mock_datetime,
        )

        assert recipe.recipe_id == 1
        assert recipe.user_id == mock_user_id
        assert recipe.title == "Test Recipe"
        assert recipe.description == "A test recipe for unit testing"
        assert recipe.origin_url == "https://example.com/recipe"
        assert recipe.servings == Decimal("4.0")
        assert recipe.preparation_time == 15
        assert recipe.cooking_time == 30
        assert recipe.difficulty == DifficultyLevelEnum.EASY
        assert recipe.created_at == mock_datetime
        assert recipe.updated_at == mock_datetime

    @pytest.mark.unit
    def test_recipe_model_creation_minimal(self, mock_user_id: uuid.UUID) -> None:
        """Test creating a Recipe instance with minimal required fields."""
        recipe = Recipe(
            user_id=mock_user_id,
            title="Minimal Recipe",
        )

        assert recipe.user_id == mock_user_id
        assert recipe.title == "Minimal Recipe"
        assert recipe.description is None
        assert recipe.origin_url is None
        assert recipe.servings is None
        assert recipe.preparation_time is None
        assert recipe.cooking_time is None
        assert recipe.difficulty is None

    @pytest.mark.unit
    def test_recipe_model_with_different_difficulties(
        self, mock_user_id: uuid.UUID
    ) -> None:
        """Test creating Recipe instances with different difficulty levels."""
        difficulties_to_test = [
            DifficultyLevelEnum.EASY,
            DifficultyLevelEnum.MEDIUM,
            DifficultyLevelEnum.HARD,
        ]

        for difficulty in difficulties_to_test:
            recipe = Recipe(
                user_id=mock_user_id,
                title=f"Recipe {difficulty.value}",
                difficulty=difficulty,
            )
            assert recipe.difficulty == difficulty

    @pytest.mark.unit
    def test_recipe_model_with_decimal_servings(self, mock_user_id: uuid.UUID) -> None:
        """Test creating Recipe instances with various decimal servings."""
        servings_to_test = [
            Decimal("1.0"),
            Decimal("2.5"),
            Decimal("4.0"),
            Decimal("12.75"),
            Decimal("0.5"),
        ]

        for servings in servings_to_test:
            recipe = Recipe(
                user_id=mock_user_id,
                title="Servings Test",
                servings=servings,
            )
            assert recipe.servings == servings

    @pytest.mark.unit
    def test_recipe_model_with_time_values(self, mock_user_id: uuid.UUID) -> None:
        """Test creating Recipe instances with various time values."""
        time_combinations = [
            (5, 10),
            (15, 30),
            (0, 60),
            (30, 0),
            (120, 240),
        ]

        for prep_time, cook_time in time_combinations:
            recipe = Recipe(
                user_id=mock_user_id,
                title="Time Test",
                preparation_time=prep_time,
                cooking_time=cook_time,
            )
            assert recipe.preparation_time == prep_time
            assert recipe.cooking_time == cook_time

    @pytest.mark.unit
    def test_recipe_model_tablename(self, mock_user_id: uuid.UUID) -> None:
        """Test that the table name is correctly set."""
        recipe = Recipe(user_id=mock_user_id, title="Test")
        assert recipe.__tablename__ == "recipes"

    @pytest.mark.unit
    def test_recipe_model_table_args(self, mock_user_id: uuid.UUID) -> None:
        """Test that the table args schema is correctly set."""
        recipe = Recipe(user_id=mock_user_id, title="Test")
        assert recipe.__table_args__ == ({"schema": "recipe_manager"},)

    @pytest.mark.unit
    def test_recipe_model_inheritance(self, mock_user_id: uuid.UUID) -> None:
        """Test that Recipe inherits from BaseDatabaseModel."""
        from app.db.models.base_database_model import BaseDatabaseModel

        recipe = Recipe(user_id=mock_user_id, title="Test")
        assert isinstance(recipe, BaseDatabaseModel)

    @pytest.mark.unit
    def test_recipe_model_serialization(
        self, mock_user_id: uuid.UUID, mock_datetime: datetime
    ) -> None:
        """Test that Recipe can be serialized to JSON."""
        recipe = Recipe(
            recipe_id=1,
            user_id=mock_user_id,
            title="Serialization Test",
            description="Test recipe for serialization",
            servings=Decimal("4.0"),
            difficulty=DifficultyLevelEnum.MEDIUM,
            created_at=mock_datetime,
            updated_at=mock_datetime,
        )

        json_str = recipe._to_json()

        # Should contain all the expected fields
        assert '"recipe_id": 1' in json_str
        assert '"title": "Serialization Test"' in json_str
        assert '"description": "Test recipe for serialization"' in json_str
        assert '"difficulty": "MEDIUM"' in json_str  # enum value

    @pytest.mark.unit
    def test_recipe_model_string_representation(self, mock_user_id: uuid.UUID) -> None:
        """Test string representation of Recipe model."""
        recipe = Recipe(
            recipe_id=1,
            user_id=mock_user_id,
            title="String Test",
        )

        str_repr = str(recipe)

        # Should be a JSON string representation
        assert '"recipe_id": 1' in str_repr
        assert '"title": "String Test"' in str_repr

    @pytest.mark.unit
    def test_recipe_model_with_none_values(self, mock_user_id: uuid.UUID) -> None:
        """Test creating Recipe with None values for optional fields."""
        recipe = Recipe(
            user_id=mock_user_id,
            title="None Values Test",
            description=None,
            origin_url=None,
            servings=None,
            preparation_time=None,
            cooking_time=None,
            difficulty=None,
        )

        assert recipe.title == "None Values Test"
        assert recipe.description is None
        assert recipe.origin_url is None
        assert recipe.servings is None
        assert recipe.preparation_time is None
        assert recipe.cooking_time is None
        assert recipe.difficulty is None

    @pytest.mark.unit
    def test_recipe_model_relationships(self, mock_user_id: uuid.UUID) -> None:
        """Test that the relationships are properly configured."""
        recipe = Recipe(user_id=mock_user_id, title="Relationship Test")

        # Relationships should be configured but initially empty lists
        assert hasattr(recipe, 'ingredients')
        assert hasattr(recipe, 'steps')
        assert hasattr(recipe, 'tags')
        assert hasattr(recipe, 'reviews')
        assert recipe.ingredients == []
        assert recipe.steps == []
        assert recipe.tags == []
        assert recipe.reviews == []

    @pytest.mark.unit
    def test_recipe_model_with_long_title(self, mock_user_id: uuid.UUID) -> None:
        """Test creating a Recipe with a long title (up to 255 chars)."""
        long_title = "A" * 255
        recipe = Recipe(user_id=mock_user_id, title=long_title)

        assert recipe.title == long_title
        assert len(recipe.title) == 255

    @pytest.mark.unit
    def test_recipe_model_with_long_description(self, mock_user_id: uuid.UUID) -> None:
        """Test creating a Recipe with a long description."""
        long_description = "This is a very long description. " * 100
        recipe = Recipe(
            user_id=mock_user_id,
            title="Long Description Test",
            description=long_description,
        )

        assert recipe.title == "Long Description Test"
        assert recipe.description == long_description

    @pytest.mark.unit
    def test_recipe_model_with_long_url(self, mock_user_id: uuid.UUID) -> None:
        """Test creating a Recipe with a long origin URL."""
        long_url = "https://example.com/very-long-recipe-url/" + "path-segment/" * 50
        recipe = Recipe(
            user_id=mock_user_id,
            title="Long URL Test",
            origin_url=long_url,
        )

        assert recipe.title == "Long URL Test"
        assert recipe.origin_url == long_url

    @pytest.mark.unit
    def test_recipe_model_with_zero_times(self, mock_user_id: uuid.UUID) -> None:
        """Test creating Recipe with zero preparation and cooking times."""
        recipe = Recipe(
            user_id=mock_user_id,
            title="Zero Times Test",
            preparation_time=0,
            cooking_time=0,
        )

        assert recipe.preparation_time == 0
        assert recipe.cooking_time == 0

    @pytest.mark.unit
    def test_recipe_model_with_fractional_servings(
        self, mock_user_id: uuid.UUID
    ) -> None:
        """Test creating Recipe with fractional servings."""
        recipe = Recipe(
            user_id=mock_user_id,
            title="Fractional Servings Test",
            servings=Decimal("2.33"),
        )

        assert recipe.servings == Decimal("2.33")
