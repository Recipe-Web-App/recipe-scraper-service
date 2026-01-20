"""Unit tests for recipe mappers.

Tests cover:
- Building downstream recipe requests from scraped data
- Building API responses from downstream responses
"""

from __future__ import annotations

import pytest

from app.llm.prompts import IngredientUnit as ParsedIngredientUnit
from app.llm.prompts import ParsedIngredient
from app.mappers import build_downstream_recipe_request, build_recipe_response
from app.schemas import CreateRecipeResponse
from app.services.recipe_management import RecipeResponse
from app.services.scraping.models import ScrapedRecipe


pytestmark = pytest.mark.unit


class TestBuildDownstreamRecipeRequest:
    """Tests for build_downstream_recipe_request mapper."""

    def test_builds_request_with_all_fields(self) -> None:
        """Should build complete downstream request from scraped and parsed data."""
        scraped = ScrapedRecipe(
            title="Chocolate Chip Cookies",
            description="Delicious homemade cookies",
            servings="24",
            prep_time=15,
            cook_time=12,
            ingredients=["2 cups flour", "1 cup sugar"],
            instructions=["Mix dry ingredients", "Add wet ingredients", "Bake"],
            source_url="https://example.com/cookies",
        )
        parsed = [
            ParsedIngredient(
                name="flour",
                quantity=2.0,
                unit=ParsedIngredientUnit.CUP,
            ),
            ParsedIngredient(
                name="sugar",
                quantity=1.0,
                unit=ParsedIngredientUnit.CUP,
            ),
        ]

        result = build_downstream_recipe_request(scraped, parsed)

        assert result.title == "Chocolate Chip Cookies"
        assert result.description == "Delicious homemade cookies"
        assert result.servings == 24.0
        assert result.preparation_time == 15
        assert result.cooking_time == 12
        assert len(result.ingredients) == 2
        assert len(result.steps) == 3

    def test_defaults_servings_to_one_when_not_parseable(self) -> None:
        """Should default servings to 1.0 when not parseable."""
        scraped = ScrapedRecipe(
            title="Test Recipe",
            description="Test",
            servings=None,
            ingredients=["1 cup flour"],
            instructions=["Mix"],
            source_url="https://example.com",
        )
        parsed = [
            ParsedIngredient(
                name="flour",
                quantity=1.0,
                unit=ParsedIngredientUnit.CUP,
            ),
        ]

        result = build_downstream_recipe_request(scraped, parsed)

        assert result.servings == 1.0

    def test_defaults_description_to_empty_string(self) -> None:
        """Should default description to empty string when None."""
        scraped = ScrapedRecipe(
            title="Test Recipe",
            description=None,
            servings="4",
            ingredients=["1 cup flour"],
            instructions=["Mix"],
            source_url="https://example.com",
        )
        parsed = [
            ParsedIngredient(
                name="flour",
                quantity=1.0,
                unit=ParsedIngredientUnit.CUP,
            ),
        ]

        result = build_downstream_recipe_request(scraped, parsed)

        assert result.description == ""

    def test_maps_ingredient_units_correctly(self) -> None:
        """Should map parsed ingredient units to downstream units."""
        scraped = ScrapedRecipe(
            title="Test Recipe",
            description="Test",
            servings="4",
            ingredients=["1 tbsp oil", "2 tsp salt"],
            instructions=["Mix"],
            source_url="https://example.com",
        )
        parsed = [
            ParsedIngredient(
                name="oil",
                quantity=1.0,
                unit=ParsedIngredientUnit.TBSP,
            ),
            ParsedIngredient(
                name="salt",
                quantity=2.0,
                unit=ParsedIngredientUnit.TSP,
            ),
        ]

        result = build_downstream_recipe_request(scraped, parsed)

        assert result.ingredients[0].unit.value == "TBSP"
        assert result.ingredients[1].unit.value == "TSP"


class TestBuildRecipeResponse:
    """Tests for build_recipe_response mapper."""

    def test_builds_response_with_all_fields(self) -> None:
        """Should build complete API response from downstream response."""
        downstream = RecipeResponse(
            id=42,
            title="Chocolate Chip Cookies",
            slug="chocolate-chip-cookies",
        )
        scraped = ScrapedRecipe(
            title="Chocolate Chip Cookies",
            description="Delicious homemade cookies",
            servings="24",
            prep_time=15,
            cook_time=12,
            ingredients=["2 cups flour"],
            instructions=["Mix ingredients", "Bake"],
            source_url="https://example.com/cookies",
        )
        parsed = [
            ParsedIngredient(
                name="flour",
                quantity=2.0,
                unit=ParsedIngredientUnit.CUP,
            ),
        ]

        result = build_recipe_response(downstream, scraped, parsed)

        assert isinstance(result, CreateRecipeResponse)
        assert result.recipe.recipe_id == 42
        assert result.recipe.title == "Chocolate Chip Cookies"
        assert result.recipe.description == "Delicious homemade cookies"
        assert result.recipe.origin_url == "https://example.com/cookies"
        assert result.recipe.servings == 24.0
        assert result.recipe.preparation_time == 15
        assert result.recipe.cooking_time == 12
        assert len(result.recipe.ingredients) == 1
        assert len(result.recipe.steps) == 2

    def test_builds_ingredients_with_quantity(self) -> None:
        """Should build ingredients with proper quantity structure."""
        downstream = RecipeResponse(id=1, title="Test", slug="test")
        scraped = ScrapedRecipe(
            title="Test",
            description="Test",
            servings="4",
            ingredients=["1 cup flour"],
            instructions=["Mix"],
            source_url="https://example.com",
        )
        parsed = [
            ParsedIngredient(
                name="flour",
                quantity=1.0,
                unit=ParsedIngredientUnit.CUP,
            ),
        ]

        result = build_recipe_response(downstream, scraped, parsed)

        ingredient = result.recipe.ingredients[0]
        assert ingredient.name == "flour"
        assert ingredient.quantity is not None
        assert ingredient.quantity.amount == 1.0
        # measurement is serialized to string due to use_enum_values=True
        assert ingredient.quantity.measurement == "CUP"

    def test_builds_steps_with_correct_numbering(self) -> None:
        """Should build steps with sequential step numbers."""
        downstream = RecipeResponse(id=1, title="Test", slug="test")
        scraped = ScrapedRecipe(
            title="Test",
            description="Test",
            servings="4",
            ingredients=["1 cup flour"],
            instructions=["First step", "Second step", "Third step"],
            source_url="https://example.com",
        )
        parsed = [
            ParsedIngredient(
                name="flour",
                quantity=1.0,
                unit=ParsedIngredientUnit.CUP,
            ),
        ]

        result = build_recipe_response(downstream, scraped, parsed)

        assert result.recipe.steps[0].step_number == 1
        assert result.recipe.steps[0].instruction == "First step"
        assert result.recipe.steps[1].step_number == 2
        assert result.recipe.steps[1].instruction == "Second step"
        assert result.recipe.steps[2].step_number == 3
        assert result.recipe.steps[2].instruction == "Third step"
