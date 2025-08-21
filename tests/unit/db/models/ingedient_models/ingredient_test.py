"""Unit tests for the Ingredient model."""

from datetime import datetime

import pytest

from app.db.models.ingredient_models.ingredient import Ingredient


class TestIngredient:
    """Test cases for Ingredient model."""

    @pytest.mark.unit
    def test_ingredient_model_creation(self, mock_datetime: datetime) -> None:
        """Test creating an Ingredient instance with all fields."""
        ingredient = Ingredient(
            ingredient_id=1,
            name="Test Ingredient",
            description="A test ingredient for unit testing",
            is_optional=False,
            created_at=mock_datetime,
            updated_at=mock_datetime,
        )

        assert ingredient.ingredient_id == 1
        assert ingredient.name == "Test Ingredient"
        assert ingredient.description == "A test ingredient for unit testing"
        assert ingredient.is_optional is False
        assert ingredient.created_at == mock_datetime
        assert ingredient.updated_at == mock_datetime

    @pytest.mark.unit
    def test_ingredient_model_creation_minimal(self) -> None:
        """Test creating an Ingredient instance with minimal required fields."""
        ingredient = Ingredient(
            name="Minimal Ingredient",
        )

        assert ingredient.name == "Minimal Ingredient"
        assert ingredient.description is None
        # Default value depends on server default, so could be None initially
        assert ingredient.is_optional in (False, None)

    @pytest.mark.unit
    def test_ingredient_model_with_optional_flag(self) -> None:
        """Test creating an Ingredient instance with is_optional=True."""
        ingredient = Ingredient(
            name="Optional Ingredient",
            is_optional=True,
        )

        assert ingredient.name == "Optional Ingredient"
        assert ingredient.is_optional is True

    @pytest.mark.unit
    def test_ingredient_model_with_none_description(self) -> None:
        """Test creating an Ingredient instance with None description."""
        ingredient = Ingredient(
            name="No Description Ingredient",
            description=None,
        )

        assert ingredient.name == "No Description Ingredient"
        assert ingredient.description is None

    @pytest.mark.unit
    def test_ingredient_model_tablename(self) -> None:
        """Test that the table name is correctly set."""
        ingredient = Ingredient(name="Test")
        assert ingredient.__tablename__ == "ingredients"

    @pytest.mark.unit
    def test_ingredient_model_table_args(self) -> None:
        """Test that the table args schema is correctly set."""
        ingredient = Ingredient(name="Test")
        assert ingredient.__table_args__ == ({"schema": "recipe_manager"},)

    @pytest.mark.unit
    def test_ingredient_model_inheritance(self) -> None:
        """Test that Ingredient inherits from BaseDatabaseModel."""
        from app.db.models.base_database_model import BaseDatabaseModel

        ingredient = Ingredient(name="Test")
        assert isinstance(ingredient, BaseDatabaseModel)

    @pytest.mark.unit
    def test_ingredient_model_serialization(self, mock_datetime: datetime) -> None:
        """Test that Ingredient can be serialized to JSON."""
        ingredient = Ingredient(
            ingredient_id=1,
            name="Serialization Test",
            description="Test ingredient for serialization",
            is_optional=True,
            created_at=mock_datetime,
            updated_at=mock_datetime,
        )

        json_str = ingredient._to_json()

        # Should contain all the expected fields
        assert '"ingredient_id": 1' in json_str
        assert '"name": "Serialization Test"' in json_str
        assert '"description": "Test ingredient for serialization"' in json_str
        assert '"is_optional": true' in json_str

    @pytest.mark.unit
    def test_ingredient_model_string_representation(self) -> None:
        """Test string representation of Ingredient model."""
        ingredient = Ingredient(
            ingredient_id=1,
            name="String Test",
        )

        str_repr = str(ingredient)

        # Should be a JSON string representation
        assert '"ingredient_id": 1' in str_repr
        assert '"name": "String Test"' in str_repr

    @pytest.mark.unit
    def test_ingredient_model_repr(self) -> None:
        """Test repr representation of Ingredient model."""
        ingredient = Ingredient(
            ingredient_id=1,
            name="Repr Test",
        )

        repr_str = repr(ingredient)

        # Should be a JSON string representation
        assert '"ingredient_id": 1' in repr_str
        assert '"name": "Repr Test"' in repr_str

    @pytest.mark.unit
    def test_ingredient_model_with_long_name(self) -> None:
        """Test creating an Ingredient with a long name (up to 255 chars)."""
        long_name = "A" * 255
        ingredient = Ingredient(name=long_name)

        assert ingredient.name == long_name
        assert len(ingredient.name) == 255

    @pytest.mark.unit
    def test_ingredient_model_with_long_description(self) -> None:
        """Test creating an Ingredient with a long description."""
        long_description = "This is a very long description. " * 100
        ingredient = Ingredient(
            name="Long Description Test",
            description=long_description,
        )

        assert ingredient.name == "Long Description Test"
        assert ingredient.description == long_description

    @pytest.mark.unit
    def test_ingredient_model_recipe_ingredients_relationship(self) -> None:
        """Test that the recipe_ingredients relationship is properly configured."""
        ingredient = Ingredient(name="Relationship Test")

        # Initially should be empty list
        assert hasattr(ingredient, 'recipe_ingredients')
        # The relationship should be configured but empty initially
        assert ingredient.recipe_ingredients == []
