"""End-to-end tests for LLM client using recorded responses.

These tests simulate realistic LLM interactions without requiring
actual GPU resources. Responses are pre-recorded from real Ollama.
"""

from __future__ import annotations

import httpx
import pytest
import respx
from pydantic import BaseModel, Field

from app.llm.client.ollama import OllamaClient
from app.llm.exceptions import LLMValidationError
from tests.fixtures.llm_responses import get_recorded_response


pytestmark = pytest.mark.e2e


class RecipeIngredient(BaseModel):
    """Ingredient in a recipe."""

    name: str
    amount: float
    unit: str


class ExtractedRecipe(BaseModel):
    """Structured recipe extraction result."""

    title: str
    ingredients: list[RecipeIngredient]
    instructions: list[str]
    prep_time_minutes: int | None = None
    cook_time_minutes: int | None = None
    servings: int | None = None


class ParsedIngredient(BaseModel):
    """Parsed ingredient from text."""

    original: str
    name: str
    amount: float
    unit: str
    preparation: str | None = None
    optional: bool = Field(default=False)


class TestRecipeExtractionE2E:
    """E2E tests for recipe extraction workflow."""

    @respx.mock
    async def test_extract_recipe_from_html(self) -> None:
        """Should extract structured recipe from scraped content."""
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=get_recorded_response("recipe_extraction"),
            )
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            cache_enabled=False,
        )

        prompt = """
        Extract the recipe from this webpage content:

        Classic Chocolate Chip Cookies
        Prep: 15 min | Cook: 11 min | Makes 48 cookies

        Ingredients:
        - 2 1/4 cups all-purpose flour
        - 1 cup butter, softened
        ...
        """

        recipe = await client.generate_structured(
            prompt=prompt,
            schema=ExtractedRecipe,
            system="You are a recipe extraction assistant. Output valid JSON.",
        )

        assert recipe.title == "Classic Chocolate Chip Cookies"
        assert len(recipe.ingredients) == 9
        assert recipe.ingredients[0].name == "all-purpose flour"
        assert recipe.ingredients[0].amount == 2.25
        assert recipe.servings == 48
        assert recipe.prep_time_minutes == 15
        assert recipe.cook_time_minutes == 11

        await client.shutdown()

    @respx.mock
    async def test_parse_ingredient_text(self) -> None:
        """Should parse ingredient text into structured format."""
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=get_recorded_response("ingredient_parsing"),
            )
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            cache_enabled=False,
        )

        ingredient = await client.generate_structured(
            prompt="Parse: 2 1/2 cups all-purpose flour, sifted",
            schema=ParsedIngredient,
        )

        assert ingredient.name == "all-purpose flour"
        assert ingredient.amount == 2.5
        assert ingredient.unit == "cups"
        assert ingredient.preparation == "sifted"
        assert ingredient.optional is False

        await client.shutdown()


class TestErrorRecoveryE2E:
    """E2E tests for error handling scenarios."""

    @respx.mock
    async def test_handles_malformed_llm_output(self) -> None:
        """Should handle malformed JSON from LLM gracefully."""
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=get_recorded_response("malformed_json"),
            )
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            cache_enabled=False,
        )

        with pytest.raises(LLMValidationError):
            await client.generate_structured(
                prompt="Extract recipe",
                schema=ExtractedRecipe,
            )

        await client.shutdown()

    @respx.mock
    async def test_raw_response_available_on_validation_error(self) -> None:
        """Should be able to get raw response even if parsing fails."""
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=get_recorded_response("malformed_json"),
            )
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            cache_enabled=False,
        )

        # Get raw response without schema validation
        result = await client.generate("Extract recipe")

        assert result.raw_response == "{ invalid json here"
        assert result.parsed is None

        await client.shutdown()


class TestSimpleGenerationE2E:
    """E2E tests for simple text generation."""

    @respx.mock
    async def test_simple_text_generation(self) -> None:
        """Should generate simple text response."""
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=get_recorded_response("simple_text"),
            )
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            cache_enabled=False,
        )

        result = await client.generate("Say hello")

        assert result.raw_response == "Hello, world!"
        assert result.model == "mistral:7b"
        assert result.cached is False

        await client.shutdown()
