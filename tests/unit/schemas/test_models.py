"""Tests for specific schema models and their validation."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.enums import (
    Allergen,
    Difficulty,
    HealthStatus,
    IngredientUnit,
    NutrientUnit,
    NutriscoreGrade,
)
from app.schemas.health import HealthCheckItem, HealthCheckResponse
from app.schemas.ingredient import Ingredient, Quantity, WebRecipe
from app.schemas.nutrition import (
    Fats,
    IngredientNutritionalInfoResponse,
    MacroNutrients,
    Minerals,
    NutrientValue,
    Vitamins,
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


class TestNutrientUnit:
    """Tests for NutrientUnit enum."""

    def test_nutrient_unit_values(self):
        """NutrientUnit should have correct values."""
        assert NutrientUnit.GRAM == "GRAM"
        assert NutrientUnit.MILLIGRAM == "MILLIGRAM"
        assert NutrientUnit.MICROGRAM == "MICROGRAM"
        assert NutrientUnit.KILOCALORIE == "KILOCALORIE"

    def test_nutrient_unit_serialization(self):
        """NutrientUnit should serialize to string value."""
        value = NutrientValue(amount=100, measurement=NutrientUnit.GRAM)
        data = value.model_dump()
        assert data["measurement"] == "GRAM"


class TestNutrientValue:
    """Tests for NutrientValue schema."""

    def test_nutrient_value_with_amount_and_unit(self):
        """NutrientValue with amount and measurement."""
        value = NutrientValue(amount=25.5, measurement=NutrientUnit.GRAM)
        assert value.amount == 25.5
        assert value.measurement == NutrientUnit.GRAM

    def test_nutrient_value_amount_non_negative(self):
        """Amount must be >= 0."""
        value = NutrientValue(amount=0, measurement=NutrientUnit.GRAM)
        assert value.amount == 0

        with pytest.raises(ValidationError):
            NutrientValue(amount=-1, measurement=NutrientUnit.GRAM)

    def test_nutrient_value_amount_optional(self):
        """Amount can be None."""
        value = NutrientValue(amount=None, measurement=NutrientUnit.GRAM)
        assert value.amount is None

    def test_nutrient_value_serializes_to_camel_case(self):
        """NutrientValue should serialize with camelCase."""
        value = NutrientValue(amount=100, measurement=NutrientUnit.MILLIGRAM)
        data = value.model_dump()
        assert "amount" in data
        assert "measurement" in data


class TestNutritionSchemas:
    """Tests for nutrition-related schemas."""

    def test_macro_nutrients_optional_fields(self):
        """MacroNutrients has all optional fields."""
        macros = MacroNutrients()
        assert macros.calories is None
        assert macros.protein is None
        assert macros.sodium is None
        assert macros.fiber is None
        assert macros.sugar is None

    def test_macro_nutrients_with_nutrient_values(self):
        """MacroNutrients accepts NutrientValue for all fields."""
        macros = MacroNutrients(
            calories=NutrientValue(amount=165, measurement=NutrientUnit.KILOCALORIE),
            protein=NutrientValue(amount=31, measurement=NutrientUnit.GRAM),
            carbs=NutrientValue(amount=0, measurement=NutrientUnit.GRAM),
            sodium=NutrientValue(amount=74, measurement=NutrientUnit.MILLIGRAM),
        )
        assert macros.calories.amount == 165
        assert macros.calories.measurement == NutrientUnit.KILOCALORIE
        assert macros.protein.amount == 31
        assert macros.sodium.amount == 74

    def test_macro_nutrients_has_flattened_fiber_sugar(self):
        """MacroNutrients has fiber and sugar as direct NutrientValue fields."""
        macros = MacroNutrients(
            fiber=NutrientValue(amount=5.5, measurement=NutrientUnit.GRAM),
            sugar=NutrientValue(amount=12.0, measurement=NutrientUnit.GRAM),
            added_sugar=NutrientValue(amount=8.0, measurement=NutrientUnit.GRAM),
        )
        assert macros.fiber.amount == 5.5
        assert macros.sugar.amount == 12.0
        assert macros.added_sugar.amount == 8.0

    def test_fats_with_nutrient_values(self):
        """Fats schema uses NutrientValue for all fat types."""
        fats = Fats(
            total=NutrientValue(amount=10.5, measurement=NutrientUnit.GRAM),
            saturated=NutrientValue(amount=3.0, measurement=NutrientUnit.GRAM),
            trans=NutrientValue(amount=0, measurement=NutrientUnit.GRAM),
        )
        assert fats.total.amount == 10.5
        assert fats.saturated.amount == 3.0
        assert fats.trans.amount == 0

    def test_fats_no_omega_fields(self):
        """Fats schema should not have omega3/6/9 fields."""
        fats = Fats(total=NutrientValue(amount=10, measurement=NutrientUnit.GRAM))
        assert not hasattr(fats, "omega3")
        assert not hasattr(fats, "omega6")
        assert not hasattr(fats, "omega9")

    def test_vitamins_with_nutrient_values(self):
        """Vitamins schema uses NutrientValue."""
        vitamins = Vitamins(
            vitamin_a=NutrientValue(amount=900, measurement=NutrientUnit.MICROGRAM),
            vitamin_c=NutrientValue(amount=15000, measurement=NutrientUnit.MICROGRAM),
            vitamin_d=NutrientValue(amount=20, measurement=NutrientUnit.MICROGRAM),
        )
        assert vitamins.vitamin_a.amount == 900
        assert vitamins.vitamin_c.amount == 15000
        assert vitamins.vitamin_c.measurement == NutrientUnit.MICROGRAM

    def test_minerals_with_nutrient_values(self):
        """Minerals schema uses NutrientValue."""
        minerals = Minerals(
            calcium=NutrientValue(amount=120, measurement=NutrientUnit.MILLIGRAM),
            iron=NutrientValue(amount=2.1, measurement=NutrientUnit.MILLIGRAM),
            zinc=NutrientValue(amount=1.0, measurement=NutrientUnit.MILLIGRAM),
        )
        assert minerals.calcium.amount == 120
        assert minerals.iron.amount == 2.1

    def test_minerals_no_sodium(self):
        """Minerals should not have sodium (moved to MacroNutrients)."""
        minerals = Minerals()
        assert not hasattr(minerals, "sodium")
        assert not hasattr(minerals, "sodium_mg")

    def test_ingredient_nutritional_info_has_usda_description(self):
        """IngredientNutritionalInfoResponse has usda_food_description field."""
        response = IngredientNutritionalInfoResponse(
            quantity=Quantity(amount=100, measurement=IngredientUnit.G),
            usda_food_description="Chicken, breast, raw",
        )
        assert response.usda_food_description == "Chicken, breast, raw"

    def test_ingredient_nutritional_info_no_classification(self):
        """IngredientNutritionalInfoResponse should not have classification field."""
        response = IngredientNutritionalInfoResponse(
            quantity=Quantity(amount=100, measurement=IngredientUnit.G),
        )
        assert not hasattr(response, "classification")

    def test_full_response_serializes_to_camel_case(self):
        """Full nutritional response serializes with camelCase."""
        response = IngredientNutritionalInfoResponse(
            quantity=Quantity(amount=100, measurement=IngredientUnit.G),
            usda_food_description="Chicken, breast, raw",
            macro_nutrients=MacroNutrients(
                calories=NutrientValue(
                    amount=165, measurement=NutrientUnit.KILOCALORIE
                ),
                protein=NutrientValue(amount=31, measurement=NutrientUnit.GRAM),
            ),
        )
        data = response.model_dump()
        assert "usdaFoodDescription" in data
        assert "macroNutrients" in data
        assert "calories" in data["macroNutrients"]
        assert data["macroNutrients"]["calories"]["amount"] == 165


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
