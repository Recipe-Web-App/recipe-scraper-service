"""Tests for specific schema models and their validation."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.enums import (
    Allergen,
    Difficulty,
    FoodGroup,
    HealthStatus,
    IngredientUnit,
    NutriscoreGrade,
)
from app.schemas.health import HealthCheckItem, HealthCheckResponse
from app.schemas.ingredient import Ingredient, Quantity, WebRecipe
from app.schemas.nutrition import (
    IngredientClassification,
    MacroNutrients,
)
from app.schemas.recipe import (
    CreateRecipeRequest,
    PopularRecipesResponse,
    Recipe,
    RecipeStep,
)
from app.schemas.recommendations import (
    ConversionRatio,
    IngredientSubstitution,
    PairingSuggestionsResponse,
)
from app.schemas.shopping import (
    IngredientShoppingInfoResponse,
    RecipeShoppingInfoResponse,
)


pytestmark = pytest.mark.unit


class TestEnumValidation:
    """Tests for enum field validation."""

    def test_ingredient_unit_valid_values(self):
        """Valid IngredientUnit values should be accepted."""
        quantity = Quantity(amount=1.5, measurement=IngredientUnit.CUP)
        assert quantity.measurement == IngredientUnit.CUP

    def test_ingredient_unit_string_coercion(self):
        """String values should be coerced to enum."""
        quantity = Quantity(amount=1.5, measurement="CUP")
        data = quantity.model_dump()
        assert data["measurement"] == "CUP"

    def test_invalid_ingredient_unit_rejected(self):
        """Invalid unit values should be rejected."""
        with pytest.raises(ValidationError):
            Quantity(amount=1.5, measurement="INVALID_UNIT")

    def test_difficulty_enum_values(self):
        """Difficulty enum should have correct values."""
        assert Difficulty.EASY == "easy"
        assert Difficulty.MEDIUM == "medium"
        assert Difficulty.HARD == "hard"

    def test_health_status_enum_values(self):
        """HealthStatus enum should have correct values."""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"

    def test_allergen_enum_comprehensive(self):
        """Allergen enum should include all common allergens."""
        assert Allergen.MILK in Allergen
        assert Allergen.EGGS in Allergen
        assert Allergen.PEANUTS in Allergen
        assert Allergen.GLUTEN in Allergen
        assert Allergen.NONE in Allergen

    def test_nutriscore_grade_values(self):
        """NutriscoreGrade should have A-E grades."""
        grades = [
            NutriscoreGrade.A,
            NutriscoreGrade.B,
            NutriscoreGrade.C,
            NutriscoreGrade.D,
            NutriscoreGrade.E,
        ]
        assert len(grades) == 5


class TestQuantitySchema:
    """Tests for Quantity schema."""

    def test_quantity_with_measurement(self):
        """Quantity with explicit measurement."""
        qty = Quantity(amount=2.5, measurement=IngredientUnit.TBSP)
        assert qty.amount == 2.5
        assert qty.measurement == IngredientUnit.TBSP

    def test_quantity_default_measurement(self):
        """Quantity defaults to UNIT measurement."""
        qty = Quantity(amount=3)
        assert qty.measurement == IngredientUnit.UNIT

    def test_quantity_amount_must_be_non_negative(self):
        """Amount must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            Quantity(amount=-1, measurement=IngredientUnit.CUP)

        errors = exc_info.value.errors()
        assert any("greater than or equal to 0" in str(err) for err in errors)

    def test_quantity_serializes_to_camel_case(self):
        """Quantity should serialize to camelCase."""
        qty = Quantity(amount=1.5, measurement=IngredientUnit.CUP)
        data = qty.model_dump()
        # amount stays as amount (single word)
        assert "amount" in data
        assert "measurement" in data


class TestIngredientSchema:
    """Tests for Ingredient schema."""

    def test_ingredient_minimal(self):
        """Ingredient with only required fields."""
        ingredient = Ingredient(ingredient_id=1)
        assert ingredient.ingredient_id == 1
        assert ingredient.name is None
        assert ingredient.quantity is None

    def test_ingredient_full(self):
        """Ingredient with all fields."""
        ingredient = Ingredient(
            ingredient_id=1,
            name="flour",
            quantity=Quantity(amount=2, measurement=IngredientUnit.CUP),
        )
        assert ingredient.name == "flour"
        assert ingredient.quantity.amount == 2

    def test_ingredient_serializes_to_camel_case(self):
        """Ingredient should serialize with camelCase."""
        ingredient = Ingredient(ingredient_id=1, name="sugar")
        data = ingredient.model_dump()
        assert "ingredientId" in data


class TestRecipeSchemas:
    """Tests for recipe-related schemas."""

    def test_recipe_step_required_fields(self):
        """RecipeStep requires step_number and instruction."""
        step = RecipeStep(step_number=1, instruction="Preheat oven")
        assert step.step_number == 1
        assert step.instruction == "Preheat oven"
        assert step.optional is False

    def test_recipe_step_optional_timer(self):
        """RecipeStep can have optional timer."""
        step = RecipeStep(
            step_number=1,
            instruction="Bake for 30 minutes",
            timer_seconds=1800,
        )
        assert step.timer_seconds == 1800

    def test_recipe_minimal(self):
        """Recipe with only required fields."""
        recipe = Recipe(
            title="Test Recipe",
            ingredients=[Ingredient(ingredient_id=1)],
            steps=[RecipeStep(step_number=1, instruction="Mix")],
        )
        assert recipe.title == "Test Recipe"
        assert recipe.recipe_id is None

    def test_recipe_serializes_to_camel_case(self):
        """Recipe should serialize with camelCase."""
        recipe = Recipe(
            recipe_id=1,
            title="Test",
            preparation_time=15,
            cooking_time=30,
            ingredients=[],
            steps=[],
        )
        data = recipe.model_dump()
        assert "recipeId" in data
        assert "preparationTime" in data
        assert "cookingTime" in data

    def test_create_recipe_request_valid_url(self):
        """CreateRecipeRequest accepts valid URL."""
        request = CreateRecipeRequest(recipe_url="https://example.com/recipe/123")
        assert str(request.recipe_url) == "https://example.com/recipe/123"

    def test_create_recipe_request_invalid_url(self):
        """CreateRecipeRequest rejects invalid URL."""
        with pytest.raises(ValidationError):
            CreateRecipeRequest(recipe_url="not-a-url")

    def test_popular_recipes_response(self):
        """PopularRecipesResponse structure."""
        response = PopularRecipesResponse(
            recipes=[
                WebRecipe(recipe_name="Mac and Cheese", url="https://example.com/1"),
            ],
            limit=50,
            offset=0,
            count=100,
        )
        assert len(response.recipes) == 1
        assert response.count == 100


class TestNutritionSchemas:
    """Tests for nutrition-related schemas."""

    def test_macro_nutrients_optional_fields(self):
        """MacroNutrients has all optional fields."""
        macros = MacroNutrients()
        assert macros.calories is None
        assert macros.protein_g is None

    def test_macro_nutrients_calories_constraint(self):
        """Calories must be non-negative."""
        macros = MacroNutrients(calories=100)
        assert macros.calories == 100

        with pytest.raises(ValidationError):
            MacroNutrients(calories=-10)

    def test_ingredient_classification_nutriscore_range(self):
        """Nutriscore must be between -15 and 40."""
        # Valid range
        classification = IngredientClassification(nutriscore_score=-15)
        assert classification.nutriscore_score == -15

        classification = IngredientClassification(nutriscore_score=40)
        assert classification.nutriscore_score == 40

        # Out of range
        with pytest.raises(ValidationError):
            IngredientClassification(nutriscore_score=-16)

        with pytest.raises(ValidationError):
            IngredientClassification(nutriscore_score=41)

    def test_ingredient_classification_with_enums(self):
        """IngredientClassification accepts enum lists."""
        classification = IngredientClassification(
            allergies=[Allergen.MILK, Allergen.EGGS],
            food_groups=[FoodGroup.DAIRY],
            nutriscore_grade=NutriscoreGrade.B,
        )
        assert len(classification.allergies) == 2
        assert classification.nutriscore_grade == NutriscoreGrade.B


class TestHealthSchemas:
    """Tests for health check schemas."""

    def test_health_check_item(self):
        """HealthCheckItem structure."""
        item = HealthCheckItem(
            status=HealthStatus.HEALTHY,
            message="Connection OK",
            response_time_ms=5.2,
        )
        assert item.status == HealthStatus.HEALTHY
        assert item.response_time_ms == 5.2

    def test_health_check_response_serialization(self):
        """HealthCheckResponse serializes with camelCase."""
        response = HealthCheckResponse(
            status=HealthStatus.HEALTHY,
            timestamp=datetime.now(UTC),
            version="2.0.0",
            uptime_seconds=3600,
            response_time_ms=45.2,
        )
        data = response.model_dump()
        assert "uptimeSeconds" in data
        assert "responseTimeMs" in data


class TestShoppingSchemas:
    """Tests for shopping info schemas."""

    def test_ingredient_shopping_info(self):
        """IngredientShoppingInfoResponse structure."""
        info = IngredientShoppingInfoResponse(
            ingredient_name="flour",
            quantity=Quantity(amount=2, measurement=IngredientUnit.CUP),
            estimated_price="2.50",
        )
        assert info.ingredient_name == "flour"
        assert info.estimated_price == "2.50"

    def test_recipe_shopping_info_id_constraint(self):
        """Recipe ID must be >= 1."""
        with pytest.raises(ValidationError):
            RecipeShoppingInfoResponse(
                recipe_id=0,
                ingredients={},
                total_estimated_cost="0.00",
            )


class TestRecommendationSchemas:
    """Tests for recommendation schemas."""

    def test_conversion_ratio_non_negative(self):
        """Conversion ratio must be >= 0."""
        ratio = ConversionRatio(ratio=0.75, measurement=IngredientUnit.CUP)
        assert ratio.ratio == 0.75

        with pytest.raises(ValidationError):
            ConversionRatio(ratio=-0.5, measurement=IngredientUnit.CUP)

    def test_ingredient_substitution(self):
        """IngredientSubstitution structure."""
        sub = IngredientSubstitution(
            ingredient="whole wheat flour",
            conversion_ratio=ConversionRatio(ratio=1.0, measurement=IngredientUnit.CUP),
        )
        assert sub.ingredient == "whole wheat flour"

    def test_pairing_suggestions_serialization(self):
        """PairingSuggestionsResponse serializes correctly."""
        response = PairingSuggestionsResponse(
            recipe_id=1,
            pairing_suggestions=[
                WebRecipe(recipe_name="Side Salad", url="https://example.com/salad"),
            ],
            limit=50,
            offset=0,
            count=10,
        )
        data = response.model_dump()
        assert "recipeId" in data
        assert "pairingSuggestions" in data
