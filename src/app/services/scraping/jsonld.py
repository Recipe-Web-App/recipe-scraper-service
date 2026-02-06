"""JSON-LD recipe extractor.

Extracts recipe data from JSON-LD structured data (schema.org/Recipe)
embedded in HTML pages. Used as a fallback when recipe-scrapers
doesn't support a website.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.observability.logging import get_logger
from app.services.scraping.models import ScrapedRecipe


logger = get_logger(__name__)


def extract_recipe_from_jsonld(html: str, source_url: str) -> ScrapedRecipe | None:
    """Extract recipe data from JSON-LD in HTML.

    Searches for schema.org/Recipe structured data in the HTML and
    extracts relevant fields.

    Args:
        html: HTML content to parse.
        source_url: Original URL for the recipe.

    Returns:
        ScrapedRecipe if found, None otherwise.
    """
    # Find all JSON-LD script blocks
    jsonld_pattern = (
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
    )
    matches = re.findall(jsonld_pattern, html, re.DOTALL | re.IGNORECASE)

    for match in matches:
        try:
            data = json.loads(match.strip())
            recipe_data = _find_recipe_in_jsonld(data)
            if recipe_data:
                return _parse_jsonld_recipe(recipe_data, source_url)
        except json.JSONDecodeError:
            continue

    return None


def _find_recipe_in_jsonld(data: Any) -> dict[str, Any] | None:
    """Find Recipe schema in JSON-LD data.

    Handles various JSON-LD structures:
    - Direct Recipe object
    - @graph array containing Recipe
    - Array of objects

    Args:
        data: Parsed JSON-LD data.

    Returns:
        Recipe dictionary if found, None otherwise.
    """
    if isinstance(data, dict):
        # Check if this is a Recipe
        schema_type = data.get("@type", "")
        if isinstance(schema_type, list):
            schema_type = " ".join(schema_type)
        if "Recipe" in str(schema_type):
            return data

        # Check @graph for Recipe
        if "@graph" in data:
            for item in data["@graph"]:
                result = _find_recipe_in_jsonld(item)
                if result:
                    return result

    elif isinstance(data, list):
        # Search array for Recipe
        for item in data:
            result = _find_recipe_in_jsonld(item)
            if result:
                return result

    return None


def _parse_jsonld_recipe(data: dict[str, Any], source_url: str) -> ScrapedRecipe:
    """Parse JSON-LD Recipe data into ScrapedRecipe model.

    Args:
        data: JSON-LD Recipe dictionary.
        source_url: Original URL.

    Returns:
        ScrapedRecipe with extracted data.
    """
    return ScrapedRecipe(
        title=_get_string(data, "name") or "Untitled Recipe",
        description=_get_string(data, "description"),
        servings=_get_yield(data),
        prep_time=_parse_duration(data.get("prepTime")),
        cook_time=_parse_duration(data.get("cookTime")),
        total_time=_parse_duration(data.get("totalTime")),
        ingredients=_get_ingredients(data),
        instructions=_get_instructions(data),
        image_url=_get_image(data),
        source_url=source_url,
        author=_get_author(data),
        cuisine=_get_string(data, "recipeCuisine"),
        category=_get_string(data, "recipeCategory"),
        keywords=_get_keywords(data),
        yields=_get_yield(data),
    )


def _get_string(
    data: dict[str, Any], key: str, default: str | None = None
) -> str | None:
    """Get a string value from the data.

    Args:
        data: Dictionary to search.
        key: Key to look for.
        default: Default value if not found.

    Returns:
        String value or default.
    """
    value = data.get(key)
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip() if value.strip() else default
    if isinstance(value, list) and value:
        return str(value[0]).strip()
    return str(value).strip() if str(value).strip() else default


def _get_yield(data: dict[str, Any]) -> str | None:
    """Extract recipe yield/servings.

    Args:
        data: Recipe JSON-LD data.

    Returns:
        Yield string or None.
    """
    yield_val = data.get("recipeYield")
    if yield_val is None:
        return None
    if isinstance(yield_val, list):
        yield_val = yield_val[0] if yield_val else None
    return str(yield_val).strip() if yield_val else None


def _parse_duration(duration: str | None) -> int | None:
    """Parse ISO 8601 duration to minutes.

    Args:
        duration: ISO 8601 duration string (e.g., "PT30M", "PT1H30M").

    Returns:
        Duration in minutes or None.
    """
    if not duration or not isinstance(duration, str):
        return None

    # Match ISO 8601 duration: PT1H30M, PT45M, PT2H, etc.
    pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
    match = re.match(pattern, duration.upper())
    if not match:
        return None

    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    # Ignore seconds, just round up if present
    seconds = int(match.group(3)) if match.group(3) else 0

    total_minutes = hours * 60 + minutes
    if seconds > 0:
        total_minutes += 1  # Round up

    return total_minutes if total_minutes > 0 else None


def _get_ingredients(data: dict[str, Any]) -> list[str]:
    """Extract ingredients list.

    Args:
        data: Recipe JSON-LD data.

    Returns:
        List of ingredient strings.
    """
    ingredients = data.get("recipeIngredient", [])
    if not isinstance(ingredients, list):
        ingredients = [ingredients] if ingredients else []
    return [str(i).strip() for i in ingredients if i and str(i).strip()]


def _get_instructions(data: dict[str, Any]) -> list[str]:
    """Extract cooking instructions.

    Handles both string and HowToStep/HowToSection formats.

    Args:
        data: Recipe JSON-LD data.

    Returns:
        List of instruction strings.
    """
    instructions = data.get("recipeInstructions", [])

    if isinstance(instructions, str):
        # Split on newlines or numbered steps
        steps = re.split(r"\n+|\d+\.\s+", instructions)
        return [s.strip() for s in steps if s.strip()]

    if not isinstance(instructions, list):
        return []

    result = []
    for item in instructions:
        if isinstance(item, str):
            result.append(item.strip())
        elif isinstance(item, dict):
            # HowToStep or HowToSection
            if item.get("@type") == "HowToSection":
                # Process section items
                section_items = item.get("itemListElement", [])
                for section_item in section_items:
                    text = _extract_instruction_text(section_item)
                    if text:
                        result.append(text)
            else:
                text = _extract_instruction_text(item)
                if text:
                    result.append(text)

    return result


def _extract_instruction_text(item: dict[str, Any] | str) -> str | None:
    """Extract text from an instruction item.

    Args:
        item: Instruction item (dict or string).

    Returns:
        Instruction text or None.
    """
    if isinstance(item, str):
        return item.strip() if item.strip() else None

    if isinstance(item, dict):
        # Try common fields
        for key in ["text", "name", "description"]:
            value = item.get(key)
            if value and isinstance(value, str):
                text: str = value.strip()
                return text

    return None


def _get_image(data: dict[str, Any]) -> str | None:
    """Extract recipe image URL.

    Args:
        data: Recipe JSON-LD data.

    Returns:
        Image URL or None.
    """
    image = data.get("image")
    if not image:
        return None

    if isinstance(image, str):
        return image

    if isinstance(image, list) and image:
        first_image = image[0]
        if isinstance(first_image, str):
            return first_image
        if isinstance(first_image, dict):
            return first_image.get("url") or first_image.get("contentUrl")

    if isinstance(image, dict):
        return image.get("url") or image.get("contentUrl")

    return None


def _get_author(data: dict[str, Any]) -> str | None:
    """Extract recipe author.

    Args:
        data: Recipe JSON-LD data.

    Returns:
        Author name or None.
    """
    author = data.get("author")
    if not author:
        return None

    if isinstance(author, str):
        return author.strip()

    if isinstance(author, list) and author:
        author = author[0]

    if isinstance(author, dict):
        return author.get("name", "").strip() or None

    return None


def _get_keywords(data: dict[str, Any]) -> list[str]:
    """Extract recipe keywords.

    Args:
        data: Recipe JSON-LD data.

    Returns:
        List of keywords.
    """
    keywords = data.get("keywords")
    if not keywords:
        return []

    if isinstance(keywords, str):
        return [k.strip() for k in keywords.split(",") if k.strip()]

    if isinstance(keywords, list):
        return [str(k).strip() for k in keywords if k and str(k).strip()]

    return []
