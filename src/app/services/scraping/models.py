"""Data models for scraped recipe data.

These models represent the raw data extracted from recipe websites
before normalization and transformation for the downstream service.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScrapedRecipe(BaseModel):
    """Raw recipe data extracted from a website.

    This model captures the data as returned by recipe-scrapers or JSON-LD,
    before any normalization or transformation. Fields are optional since
    different sources may provide different subsets of data.
    """

    title: str = Field(..., description="Recipe title")
    description: str | None = Field(None, description="Recipe description")
    servings: str | None = Field(None, description="Number of servings (as string)")
    prep_time: int | None = Field(None, description="Prep time in minutes")
    cook_time: int | None = Field(None, description="Cook time in minutes")
    total_time: int | None = Field(None, description="Total time in minutes")
    ingredients: list[str] = Field(
        default_factory=list, description="Raw ingredient strings"
    )
    instructions: list[str] = Field(
        default_factory=list, description="Cooking instructions"
    )
    image_url: str | None = Field(None, description="Main recipe image URL")
    source_url: str = Field(..., description="Original URL the recipe was scraped from")
    author: str | None = Field(None, description="Recipe author")
    cuisine: str | None = Field(None, description="Cuisine type")
    category: str | None = Field(None, description="Recipe category")
    keywords: list[str] = Field(
        default_factory=list, description="Recipe keywords/tags"
    )
    yields: str | None = Field(None, description="Recipe yield (e.g., '12 cookies')")
    difficulty: str | None = Field(None, description="Difficulty level if available")

    def parse_servings(self) -> float | None:
        """Parse servings string to float.

        Returns:
            Parsed servings as float, or None if parsing fails.
        """
        if not self.servings:
            return None
        try:
            # Handle common formats like "4", "4 servings", "4-6"
            servings_str = self.servings.lower().replace("servings", "").strip()
            # Take first number if range
            if "-" in servings_str:
                servings_str = servings_str.split("-")[0].strip()
            return float(servings_str)
        except (ValueError, IndexError):
            return None
