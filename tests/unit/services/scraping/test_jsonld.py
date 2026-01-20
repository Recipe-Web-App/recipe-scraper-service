"""Unit tests for JSON-LD recipe extractor."""

from __future__ import annotations

import pytest

from app.services.scraping.jsonld import (
    _parse_duration,
    extract_recipe_from_jsonld,
)


pytestmark = pytest.mark.unit


class TestParseDuration:
    """Tests for ISO 8601 duration parsing."""

    def test_parses_minutes_only(self) -> None:
        """Should parse PT30M to 30 minutes."""
        assert _parse_duration("PT30M") == 30

    def test_parses_hours_only(self) -> None:
        """Should parse PT2H to 120 minutes."""
        assert _parse_duration("PT2H") == 120

    def test_parses_hours_and_minutes(self) -> None:
        """Should parse PT1H30M to 90 minutes."""
        assert _parse_duration("PT1H30M") == 90

    def test_parses_with_seconds_rounds_up(self) -> None:
        """Should round up when seconds are present."""
        assert _parse_duration("PT30M45S") == 31

    def test_returns_none_for_invalid_format(self) -> None:
        """Should return None for invalid duration strings."""
        assert _parse_duration("invalid") is None
        assert _parse_duration("30 minutes") is None

    def test_returns_none_for_none_input(self) -> None:
        """Should return None for None input."""
        assert _parse_duration(None) is None

    def test_returns_none_for_empty_string(self) -> None:
        """Should return None for empty string."""
        assert _parse_duration("") is None

    def test_handles_lowercase(self) -> None:
        """Should handle lowercase duration strings."""
        assert _parse_duration("pt1h30m") == 90


class TestExtractRecipeFromJsonLD:
    """Tests for JSON-LD recipe extraction."""

    def test_extracts_basic_recipe(self) -> None:
        """Should extract recipe from basic JSON-LD."""
        html = """
        <html>
        <head>
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test Recipe",
            "description": "A test recipe",
            "recipeYield": "4 servings",
            "prepTime": "PT15M",
            "cookTime": "PT30M",
            "recipeIngredient": ["1 cup flour", "2 eggs"],
            "recipeInstructions": ["Mix ingredients", "Bake at 350F"]
        }
        </script>
        </head>
        </html>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")

        assert recipe is not None
        assert recipe.title == "Test Recipe"
        assert recipe.description == "A test recipe"
        assert recipe.servings == "4 servings"
        assert recipe.prep_time == 15
        assert recipe.cook_time == 30
        assert recipe.ingredients == ["1 cup flour", "2 eggs"]
        assert recipe.instructions == ["Mix ingredients", "Bake at 350F"]
        assert recipe.source_url == "https://example.com/recipe"

    def test_extracts_recipe_from_graph(self) -> None:
        """Should extract recipe from @graph structure."""
        html = """
        <html>
        <script type="application/ld+json">
        {
            "@graph": [
                {"@type": "WebSite", "name": "Cooking Site"},
                {"@type": "Recipe", "name": "Graph Recipe"}
            ]
        }
        </script>
        </html>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")

        assert recipe is not None
        assert recipe.title == "Graph Recipe"

    def test_extracts_recipe_from_array(self) -> None:
        """Should extract recipe from array of JSON-LD objects."""
        html = """
        <html>
        <script type="application/ld+json">
        [
            {"@type": "WebSite", "name": "Cooking Site"},
            {"@type": "Recipe", "name": "Array Recipe"}
        ]
        </script>
        </html>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")

        assert recipe is not None
        assert recipe.title == "Array Recipe"

    def test_extracts_howto_instructions(self) -> None:
        """Should extract instructions from HowToStep format."""
        html = """
        <html>
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "HowTo Recipe",
            "recipeInstructions": [
                {"@type": "HowToStep", "text": "Step 1 text"},
                {"@type": "HowToStep", "text": "Step 2 text"}
            ]
        }
        </script>
        </html>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")

        assert recipe is not None
        assert recipe.instructions == ["Step 1 text", "Step 2 text"]

    def test_extracts_image_url(self) -> None:
        """Should extract image URL from various formats."""
        # Test string image
        html = """
        <script type="application/ld+json">
        {"@type": "Recipe", "name": "Test", "image": "https://example.com/image.jpg"}
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.image_url == "https://example.com/image.jpg"

    def test_extracts_image_from_object(self) -> None:
        """Should extract image URL from ImageObject."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "image": {"@type": "ImageObject", "url": "https://example.com/image.jpg"}
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.image_url == "https://example.com/image.jpg"

    def test_extracts_author(self) -> None:
        """Should extract author from Person object."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "author": {"@type": "Person", "name": "John Doe"}
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.author == "John Doe"

    def test_returns_none_when_no_recipe_found(self) -> None:
        """Should return None when no Recipe schema found."""
        html = """
        <html>
        <script type="application/ld+json">
        {"@type": "WebSite", "name": "Not a recipe"}
        </script>
        </html>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is None

    def test_returns_none_for_invalid_json(self) -> None:
        """Should return None for invalid JSON."""
        html = """
        <script type="application/ld+json">
        {invalid json}
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is None

    def test_returns_none_for_no_jsonld(self) -> None:
        """Should return None when no JSON-LD present."""
        html = "<html><body>No JSON-LD here</body></html>"
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is None

    def test_extracts_keywords(self) -> None:
        """Should extract keywords from comma-separated string."""
        html = """
        <script type="application/ld+json">
        {"@type": "Recipe", "name": "Test", "keywords": "easy, quick, dinner"}
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.keywords == ["easy", "quick", "dinner"]

    def test_handles_type_array(self) -> None:
        """Should handle @type as array."""
        html = """
        <script type="application/ld+json">
        {"@type": ["Recipe", "HowTo"], "name": "Multi-type Recipe"}
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.title == "Multi-type Recipe"

    def test_extracts_string_as_list_value(self) -> None:
        """Should extract first element when value is a list."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": ["First Name", "Second Name"],
            "description": ["First desc", "Second desc"]
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.title == "First Name"
        assert recipe.description == "First desc"

    def test_extracts_yield_from_list(self) -> None:
        """Should extract yield from list format."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "recipeYield": ["4 servings", "8 portions"]
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.servings == "4 servings"

    def test_handles_empty_yield_list(self) -> None:
        """Should handle empty yield list."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "recipeYield": []
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.servings is None

    def test_extracts_single_ingredient_not_in_list(self) -> None:
        """Should handle single ingredient not wrapped in list."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "recipeIngredient": "1 cup flour"
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.ingredients == ["1 cup flour"]

    def test_extracts_instructions_from_string(self) -> None:
        """Should split string instructions on newlines."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "recipeInstructions": "Mix the ingredients.\\nBake at 350F.\\nCool before serving."
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert len(recipe.instructions) == 3
        assert "Mix the ingredients." in recipe.instructions

    def test_extracts_instructions_from_numbered_string(self) -> None:
        """Should split numbered string instructions."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "recipeInstructions": "1. Mix the ingredients. 2. Bake at 350F. 3. Cool."
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert len(recipe.instructions) >= 2

    def test_handles_non_list_non_string_instructions(self) -> None:
        """Should return empty list for invalid instructions type."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "recipeInstructions": 12345
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.instructions == []

    def test_extracts_howto_section_instructions(self) -> None:
        """Should extract instructions from HowToSection format."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "recipeInstructions": [
                {
                    "@type": "HowToSection",
                    "name": "Preparation",
                    "itemListElement": [
                        {"@type": "HowToStep", "text": "Prep step 1"},
                        {"@type": "HowToStep", "text": "Prep step 2"}
                    ]
                },
                {
                    "@type": "HowToSection",
                    "name": "Cooking",
                    "itemListElement": [
                        {"@type": "HowToStep", "text": "Cook step 1"}
                    ]
                }
            ]
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert len(recipe.instructions) == 3
        assert "Prep step 1" in recipe.instructions
        assert "Cook step 1" in recipe.instructions

    def test_extracts_instruction_with_name_field(self) -> None:
        """Should extract instruction text from name field."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "recipeInstructions": [
                {"@type": "HowToStep", "name": "Step with name only"}
            ]
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.instructions == ["Step with name only"]

    def test_extracts_instruction_with_description_field(self) -> None:
        """Should extract instruction text from description field."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "recipeInstructions": [
                {"@type": "HowToStep", "description": "Step with description only"}
            ]
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.instructions == ["Step with description only"]

    def test_skips_instruction_without_text(self) -> None:
        """Should skip instruction dict without text/name/description."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "recipeInstructions": [
                {"@type": "HowToStep", "url": "https://example.com"},
                {"@type": "HowToStep", "text": "Valid step"}
            ]
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.instructions == ["Valid step"]

    def test_extracts_image_from_array_of_strings(self) -> None:
        """Should extract first image from array of strings."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "image": ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.image_url == "https://example.com/img1.jpg"

    def test_extracts_image_from_array_of_objects(self) -> None:
        """Should extract image URL from array of ImageObjects."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "image": [
                {"@type": "ImageObject", "url": "https://example.com/img1.jpg"},
                {"@type": "ImageObject", "url": "https://example.com/img2.jpg"}
            ]
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.image_url == "https://example.com/img1.jpg"

    def test_extracts_image_contenturl(self) -> None:
        """Should extract image from contentUrl field."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "image": {"@type": "ImageObject", "contentUrl": "https://example.com/content.jpg"}
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.image_url == "https://example.com/content.jpg"

    def test_extracts_author_string(self) -> None:
        """Should extract author from string."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "author": "John Doe"
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.author == "John Doe"

    def test_extracts_author_from_array(self) -> None:
        """Should extract first author from array."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "author": [
                {"@type": "Person", "name": "First Author"},
                {"@type": "Person", "name": "Second Author"}
            ]
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.author == "First Author"

    def test_returns_none_for_author_without_name(self) -> None:
        """Should return None for author dict without name."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "author": {"@type": "Person", "url": "https://example.com"}
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.author is None

    def test_extracts_keywords_from_array(self) -> None:
        """Should extract keywords from array format."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "keywords": ["easy", "quick", "dinner"]
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.keywords == ["easy", "quick", "dinner"]

    def test_returns_empty_keywords_for_invalid_type(self) -> None:
        """Should return empty list for invalid keywords type."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "keywords": 12345
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.keywords == []

    def test_handles_graph_without_recipe(self) -> None:
        """Should return None when @graph contains no Recipe."""
        html = """
        <script type="application/ld+json">
        {
            "@graph": [
                {"@type": "WebSite", "name": "Site"},
                {"@type": "Organization", "name": "Org"}
            ]
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is None

    def test_handles_empty_string_value(self) -> None:
        """Should handle empty string values correctly."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test",
            "description": "   "
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.description is None

    def test_handles_numeric_value_as_string(self) -> None:
        """Should convert numeric values to strings."""
        html = """
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": 12345,
            "recipeYield": 4
        }
        </script>
        """
        recipe = extract_recipe_from_jsonld(html, "https://example.com/recipe")
        assert recipe is not None
        assert recipe.title == "12345"
        assert recipe.servings == "4"
