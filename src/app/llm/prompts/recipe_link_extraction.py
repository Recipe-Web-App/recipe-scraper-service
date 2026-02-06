"""Recipe link extraction prompt for LLM-based link identification.

This module defines the prompt and output schema for extracting recipe links
from HTML pages, filtering out navigation and category links.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from .base import BasePrompt


class ExtractedRecipeLink(BaseModel):
    """A single recipe link extracted from HTML."""

    model_config = ConfigDict(extra="ignore")

    recipe_name: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="The recipe title/name (e.g., 'Garlic Butter Chicken')",
    )
    url: str = Field(
        ...,
        description="The URL path or full URL to the recipe page",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1) that this is a real recipe link",
    )


class ExtractedRecipeLinkList(BaseModel):
    """Output schema for recipe link extraction."""

    model_config = ConfigDict(extra="ignore")

    recipe_links: list[ExtractedRecipeLink] = Field(
        default_factory=list,
        description="List of recipe links found on the page",
    )


class RecipeLinkExtractionPrompt(BasePrompt[ExtractedRecipeLinkList]):
    """Prompt for extracting recipe links from HTML listing pages.

    Example input:
        HTML containing recipe cards with links to individual recipes

    Example output:
        {
            "recipe_links": [
                {
                    "recipe_name": "Garlic Butter Chicken",
                    "url": "/recipe/12345/garlic-butter-chicken",
                    "confidence": 1.0
                },
                {
                    "recipe_name": "Classic Chocolate Cake",
                    "url": "/recipes/classic-chocolate-cake",
                    "confidence": 0.9
                }
            ]
        }
    """

    output_schema: ClassVar[type[BaseModel]] = ExtractedRecipeLinkList

    system_prompt: ClassVar[
        str | None
    ] = """You are an expert at extracting INDIVIDUAL RECIPE links from HTML pages.
Your task is to find links to SPECIFIC DISHES, not category or collection pages.

INCLUDE only links that:
- Point to a SINGLE SPECIFIC RECIPE (e.g., "Garlic Butter Chicken", "Creamy White Chili", "Banh Tet")
- Have a URL with /recipe/ or /recipes/ followed by a dish name slug (e.g., /recipes/creamy-white-chili/, /recipe/284441/banh-tet/)
- Name a specific dish you could actually cook (not a category of dishes)

EXCLUDE links that:
- Are CATEGORY or COLLECTION pages - look for category words in URL: "everyday-cooking", "holidays", "family-dinners", "quick-and-easy"
- Are named after meal types or categories: "Dinners", "Desserts", "Quick Meals", "One-Pot Meals", "Comfort Food", "Family Dinners"
- Are guides or tips: "Grilling Guides", "Baking Guides", "Tips & Troubleshooting"
- Are user actions: "Log In", "Sign Up", "Save Recipe"
- Are navigation: "Read More", "View All", "See More"

HOW TO IDENTIFY INDIVIDUAL RECIPES:
- URL slug is a specific dish name: /recipes/creamy-white-chili/ or /recipe/284441/banh-tet/
- The link text or URL contains a food item you could actually cook

RECIPE NAME HANDLING:
- If link text is generic ("Get Recipe", "View Recipe"), extract recipe name from URL slug
- Convert slug to title case: "creamy-white-chili" → "Creamy White Chili"

Set confidence to:
- 1.0: URL slug is a specific dish name AND link text is a food name
- 0.8: URL slug is a specific dish name but link text is generic
- Below 0.5: Category page, guide, or navigation (exclude)

Return URLs exactly as they appear in the HTML."""

    temperature: ClassVar[float] = 0.0  # Deterministic extraction
    max_tokens: ClassVar[int | None] = 4096

    def format(self, **kwargs: Any) -> str:
        """Format the prompt with HTML content and base URL.

        Args:
            **kwargs: Must contain 'html_content' and 'base_url' keys.

        Returns:
            Formatted prompt string.

        Raises:
            ValueError: If required arguments are missing.
        """
        html_content = kwargs.get("html_content")
        base_url = kwargs.get("base_url")

        if html_content is None:
            msg = "Missing required 'html_content' argument"
            raise ValueError(msg)
        if base_url is None:
            msg = "Missing required 'base_url' argument"
            raise ValueError(msg)

        return f"""Extract all recipe links from this HTML content.
The base URL for this website is: {base_url}
Use this to understand the site structure, but return URLs exactly as they appear in the HTML.

HTML Content:
{html_content}

Return a JSON object with a "recipe_links" array containing objects with "recipe_name", "url", and "confidence" fields."""
