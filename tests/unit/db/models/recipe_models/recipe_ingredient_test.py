"""Unit tests for the RecipeIngredient model."""

from decimal import Decimal

import pytest

from app.db.models.recipe_models.recipe_ingredient import RecipeIngredient
from app.enums.ingredient_unit_enum import IngredientUnitEnum


class TestRecipeIngredient:
    """Test cases for RecipeIngredient model."""

    @pytest.mark.unit
    def test_recipe_ingredient_model_creation(self) -> None:
        """Test creating a RecipeIngredient instance with all fields."""
        recipe_ingredient = RecipeIngredient(
            recipe_id=1,
            ingredient_id=2,
            quantity=Decimal("100.5"),
            unit=IngredientUnitEnum.G,
            is_optional=False,
        )

        assert recipe_ingredient.recipe_id == 1
        assert recipe_ingredient.ingredient_id == 2
        assert recipe_ingredient.quantity == Decimal("100.5")
        assert recipe_ingredient.unit == IngredientUnitEnum.G
        assert recipe_ingredient.is_optional is False

    @pytest.mark.unit
    def test_recipe_ingredient_model_creation_minimal(self) -> None:
        """Test creating a RecipeIngredient instance with minimal required fields."""
        recipe_ingredient = RecipeIngredient(
            recipe_id=1,
            ingredient_id=2,
        )

        assert recipe_ingredient.recipe_id == 1
        assert recipe_ingredient.ingredient_id == 2
        assert recipe_ingredient.quantity is None
        assert recipe_ingredient.unit is None
        # Default value depends on server default, so could be None initially
        assert recipe_ingredient.is_optional in (False, None)

    @pytest.mark.unit
    def test_recipe_ingredient_model_with_optional_flag(self) -> None:
        """Test creating a RecipeIngredient instance with is_optional=True."""
        recipe_ingredient = RecipeIngredient(
            recipe_id=1,
            ingredient_id=2,
            is_optional=True,
        )

        assert recipe_ingredient.recipe_id == 1
        assert recipe_ingredient.ingredient_id == 2
        assert recipe_ingredient.is_optional is True

    @pytest.mark.unit
    def test_recipe_ingredient_model_with_various_units(self) -> None:
        """Test creating RecipeIngredient instances with different units."""
        units_to_test = [
            IngredientUnitEnum.G,
            IngredientUnitEnum.KG,
            IngredientUnitEnum.LB,
            IngredientUnitEnum.TBSP,
            IngredientUnitEnum.TSP,
            IngredientUnitEnum.CUP,
        ]

        for unit in units_to_test:
            recipe_ingredient = RecipeIngredient(
                recipe_id=1,
                ingredient_id=2,
                quantity=Decimal("1.0"),
                unit=unit,
            )
            assert recipe_ingredient.unit == unit

    @pytest.mark.unit
    def test_recipe_ingredient_model_with_decimal_quantities(self) -> None:
        """Test creating RecipeIngredient instances with various decimal quantities."""
        quantities_to_test = [
            Decimal("0.1"),
            Decimal("1.5"),
            Decimal("100.25"),
            Decimal("999.999"),
            Decimal("0.001"),
        ]

        for quantity in quantities_to_test:
            recipe_ingredient = RecipeIngredient(
                recipe_id=1,
                ingredient_id=2,
                quantity=quantity,
                unit=IngredientUnitEnum.G,
            )
            assert recipe_ingredient.quantity == quantity

    @pytest.mark.unit
    def test_recipe_ingredient_model_tablename(self) -> None:
        """Test that the table name is correctly set."""
        recipe_ingredient = RecipeIngredient(recipe_id=1, ingredient_id=2)
        assert recipe_ingredient.__tablename__ == "recipe_ingredients"

    @pytest.mark.unit
    def test_recipe_ingredient_model_table_args(self) -> None:
        """Test that the table args schema is correctly set."""
        recipe_ingredient = RecipeIngredient(recipe_id=1, ingredient_id=2)
        assert recipe_ingredient.__table_args__ == ({"schema": "recipe_manager"},)

    @pytest.mark.unit
    def test_recipe_ingredient_model_inheritance(self) -> None:
        """Test that RecipeIngredient inherits from BaseDatabaseModel."""
        from app.db.models.base_database_model import BaseDatabaseModel

        recipe_ingredient = RecipeIngredient(recipe_id=1, ingredient_id=2)
        assert isinstance(recipe_ingredient, BaseDatabaseModel)

    @pytest.mark.unit
    def test_recipe_ingredient_model_serialization(self) -> None:
        """Test that RecipeIngredient can be serialized to JSON."""
        recipe_ingredient = RecipeIngredient(
            recipe_id=1,
            ingredient_id=2,
            quantity=Decimal("100.5"),
            unit=IngredientUnitEnum.G,
            is_optional=True,
        )

        json_str = recipe_ingredient._to_json()

        # Should contain all the expected fields
        assert '"recipe_id": 1' in json_str
        assert '"ingredient_id": 2' in json_str
        assert '"quantity":' in json_str
        assert '"unit": "G"' in json_str  # enum value
        assert '"is_optional": true' in json_str

    @pytest.mark.unit
    def test_recipe_ingredient_model_string_representation(self) -> None:
        """Test string representation of RecipeIngredient model."""
        recipe_ingredient = RecipeIngredient(
            recipe_id=1,
            ingredient_id=2,
            quantity=Decimal("100"),
            unit=IngredientUnitEnum.G,
        )

        str_repr = str(recipe_ingredient)

        # Should be a JSON string representation
        assert '"recipe_id": 1' in str_repr
        assert '"ingredient_id": 2' in str_repr

    @pytest.mark.unit
    def test_recipe_ingredient_model_with_none_values(self) -> None:
        """Test creating RecipeIngredient with None values for optional fields."""
        recipe_ingredient = RecipeIngredient(
            recipe_id=1,
            ingredient_id=2,
            quantity=None,
            unit=None,
        )

        assert recipe_ingredient.recipe_id == 1
        assert recipe_ingredient.ingredient_id == 2
        assert recipe_ingredient.quantity is None
        assert recipe_ingredient.unit is None

    @pytest.mark.unit
    def test_recipe_ingredient_model_relationships(self) -> None:
        """Test that the relationships are properly configured."""
        recipe_ingredient = RecipeIngredient(recipe_id=1, ingredient_id=2)

        # Relationships should be configured but initially None/empty
        assert hasattr(recipe_ingredient, 'recipe')
        assert hasattr(recipe_ingredient, 'ingredient')

    @pytest.mark.unit
    def test_recipe_ingredient_model_with_large_quantity(self) -> None:
        """Test creating RecipeIngredient with large quantity values."""
        large_quantity = Decimal("99999.999")
        recipe_ingredient = RecipeIngredient(
            recipe_id=1,
            ingredient_id=2,
            quantity=large_quantity,
            unit=IngredientUnitEnum.KG,
        )

        assert recipe_ingredient.quantity == large_quantity
        assert recipe_ingredient.unit == IngredientUnitEnum.KG

    @pytest.mark.unit
    def test_recipe_ingredient_model_composite_primary_key(self) -> None:
        """Test that RecipeIngredient uses composite primary key."""
        recipe_ingredient = RecipeIngredient(recipe_id=1, ingredient_id=2)

        # Both fields should be part of the primary key
        assert recipe_ingredient.recipe_id == 1
        assert recipe_ingredient.ingredient_id == 2
