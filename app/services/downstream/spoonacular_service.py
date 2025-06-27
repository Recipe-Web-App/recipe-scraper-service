"""Spoonacular API service for ingredient substitutions.

This service provides ingredient substitution functionality using the Spoonacular API,
which offers a reliable database of cooking ingredient substitutes.
"""

import re
from http import HTTPStatus
from typing import Any

import httpx
from fastapi import HTTPException

from app.api.v1.schemas.downstream.spoonacular import (
    SpoonacularSimilarRecipesResponse,
    SpoonacularSubstitutesResponse,
)
from app.core.config.config import settings
from app.core.logging import get_logger
from app.enums.ingredient_unit_enum import IngredientUnitEnum
from app.exceptions.custom_exceptions import SubstitutionNotFoundError

_log = get_logger(__name__)

# HTTP status codes
HTTP_PAYMENT_REQUIRED = 402
HTTP_NOT_FOUND = 404


class SpoonacularService:
    """Service for interacting with Spoonacular's ingredient substitution API."""

    def __init__(self) -> None:
        """Initialize the Spoonacular service."""
        self.api_key = settings.spoonacular_api_key
        self.base_url = "https://api.spoonacular.com"
        self.client = httpx.Client(timeout=30.0)

    def __del__(self) -> None:
        """Clean up HTTP client."""
        if hasattr(self, "client"):
            self.client.close()

    def get_ingredient_substitutes(
        self,
        ingredient_name: str,
    ) -> list[dict[str, Any]]:
        """Get ingredient substitutes from Spoonacular API.

        Args:
            ingredient_name: Name of the ingredient to find substitutes for

        Returns:
            List of ingredient substitutes with conversion information

        Raises:
            Exception: If API call fails
        """
        try:
            _log.debug("Getting substitutes for ingredient: {}", ingredient_name)

            # Spoonacular's ingredient substitutes endpoint
            url = f"{self.base_url}/food/ingredients/substitutes"

            params = {
                "ingredientName": ingredient_name,
                "apiKey": self.api_key,
            }

            response = self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            _log.debug(
                "Spoonacular API call successful for '{}', found {} substitutes",
                ingredient_name,
                len(data.get("substitutes", [])),
            )

            return self._parse_spoonacular_response(data, ingredient_name)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == HTTPStatus.PAYMENT_REQUIRED:
                _log.error("Spoonacular API quota exceeded or payment required")
                raise HTTPException(
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                    detail=(
                        "Ingredient substitution service temporarily unavailable "
                        "due to quota limits"
                    ),
                ) from e

            if e.response.status_code == HTTPStatus.NOT_FOUND:
                _log.warning("No substitutes found for ingredient: {}", ingredient_name)
                raise SubstitutionNotFoundError(
                    ingredient_name=ingredient_name,
                    reason="Spoonacular API returned no results for this ingredient",
                ) from e

            _log.error("Spoonacular API HTTP error {}: {}", e.response.status_code, e)
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail="Ingredient substitution service temporarily unavailable",
            ) from e

        except httpx.RequestError as e:
            _log.error(
                "Spoonacular API request failed for '{}': {}",
                ingredient_name,
                e,
            )
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Ingredient substitution service temporarily unavailable",
            ) from e

    def _parse_spoonacular_response(
        self,
        data: dict[str, Any],
        original_ingredient: str,
    ) -> list[dict[str, Any]]:
        """Parse Spoonacular API response into standardized format.

        Args:
            data: Raw response from Spoonacular API
            original_ingredient: Original ingredient name for logging

        Returns:
            List of standardized substitute information
        """
        # Parse the raw response using the Pydantic model
        try:
            spoonacular_response = SpoonacularSubstitutesResponse(**data)
        except (ValueError, TypeError) as e:
            _log.error(
                "Failed to parse Spoonacular response for '{}': {}",
                original_ingredient,
                e,
            )
            raise SubstitutionNotFoundError(
                ingredient_name=original_ingredient,
                reason="Invalid response format from Spoonacular API",
            ) from e

        # Check if Spoonacular returned a failure response
        if spoonacular_response.status == "failure":
            error_message = (
                spoonacular_response.message or "Unknown error from Spoonacular API"
            )
            _log.warning(
                "Spoonacular API returned failure for '{}': {}",
                original_ingredient,
                error_message,
            )
            raise SubstitutionNotFoundError(
                ingredient_name=original_ingredient,
                reason=error_message,
            )

        substitutes = []

        # Process each substitute item using the model's helper methods
        for substitute_item in spoonacular_response.substitutes:
            raw_ingredient_text = spoonacular_response.get_ingredient_name(
                substitute_item,
            )
            description = spoonacular_response.get_description(substitute_item)

            if not raw_ingredient_text:
                continue

            # Extract clean ingredient name from the raw text
            clean_ingredient_name = self._extract_clean_ingredient_name(
                raw_ingredient_text,
            )

            ratio_value = self._extract_ratio_from_description(description)

            substitutes.append(
                {
                    "substitute_ingredient": clean_ingredient_name,
                    "conversion_ratio": {
                        "ratio": ratio_value,
                        "measurement": IngredientUnitEnum.find_unit_in_text(
                            description,
                        ),
                    },
                    "notes": description,
                    "confidence_score": 0.8,  # Default for Spoonacular data
                },
            )

        _log.info(
            "Parsed {} substitutes for '{}' from Spoonacular",
            len(substitutes),
            original_ingredient,
        )

        # If no substitutes were found, raise appropriate exception
        if not substitutes:
            _log.warning(
                "No valid substitutes found for ingredient: {}",
                original_ingredient,
            )
            raise SubstitutionNotFoundError(
                ingredient_name=original_ingredient,
                reason="No valid substitutes found in Spoonacular response",
            )

        return substitutes

    def _extract_ratio_from_description(self, description: str) -> float:
        """Extract conversion ratio from description text.

        Args:
            description: Description text that may contain ratio information

        Returns:
            Conversion ratio (defaults to 1.0 if not found)
        """
        # Common ratio patterns in descriptions
        ratio_patterns = [
            r"(\d+(?:\.\d+)?)\s*:\s*1",  # "2:1", "1.5:1"
            r"(\d+(?:\.\d+)?)\s*times",  # "2 times", "1.5 times"
            r"(\d+(?:\.\d+)?)\s*x",  # "2x", "1.5x"
            r"use\s+(\d+(?:\.\d+)?)",  # "use 2", "use 1.5"
        ]

        for pattern in ratio_patterns:
            match = re.search(pattern, description.lower())
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue

        # Default ratio
        return 1.0

    def _extract_clean_ingredient_name(self, raw_ingredient_text: str) -> str:
        """Extract clean ingredient name from Spoonacular format.

        Handles formats like:
        - "1 cup = 1 cup American cheese" -> "American Cheese"
        - "2 tablespoons = 1 ounce cream cheese" -> "Cream Cheese"

        Args:
            raw_ingredient_text: Raw text from Spoonacular API

        Returns:
            Clean ingredient name without ratio/quantity information, title cased
        """
        clean_name = ""

        # Handle format like "1 cup = 1 cup American cheese"
        if " = " in raw_ingredient_text:
            # Extract the part after the equals sign
            ingredient_part = raw_ingredient_text.split(" = ", 1)[1].strip()

            # Remove leading quantity/unit from "1 cup American cheese"
            parts = ingredient_part.split()
            min_parts_with_unit = 3  # quantity + unit + ingredient

            if len(parts) >= min_parts_with_unit:
                # Skip first two parts (quantity and unit) and join the rest
                clean_name = " ".join(parts[2:])
            else:
                clean_name = ingredient_part
        else:
            # For other formats, extract name before parentheses or dashes
            clean_name = raw_ingredient_text.split(" (")[0].split(" -")[0].strip()

        # Convert to title case (capitalize first letter of each word)
        return clean_name.title()

    def get_similar_recipes(
        self,
        recipe_id: int,
        number: int = 10,
    ) -> list[dict[str, Any]]:
        """Get similar recipes from Spoonacular API.

        Args:
            recipe_id: Spoonacular recipe ID to find similar recipes for
            number: Number of similar recipes to return

        Returns:
            List of similar recipes with standardized format

        Raises:
            HTTPException: If API call fails or no similar recipes found
        """
        try:
            _log.debug(
                "Getting similar recipes for Spoonacular recipe ID: {}",
                recipe_id,
            )

            # Spoonacular's similar recipes endpoint
            url = f"{self.base_url}/recipes/{recipe_id}/similar"

            params = {
                "number": min(number, 100),  # Spoonacular limit
                "apiKey": self.api_key,
            }

            response = self.client.get(url, params=params)
            response.raise_for_status()

            # Similar recipes endpoint returns a list directly
            recipe_list = response.json()

            _log.debug(
                "Spoonacular similar recipes API call successful, found {} recipes",
                len(recipe_list),
            )

            # Parse the response using our schema
            similar_response = SpoonacularSimilarRecipesResponse.from_list(recipe_list)
            return self._convert_recipes_to_standard_format(similar_response.recipes)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == HTTPStatus.PAYMENT_REQUIRED:
                _log.error("Spoonacular API quota exceeded or payment required")
                raise HTTPException(
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                    detail=(
                        "Recipe recommendation service temporarily unavailable "
                        "due to quota limits"
                    ),
                ) from e

            if e.response.status_code == HTTPStatus.NOT_FOUND:
                _log.warning("No similar recipes found for recipe ID: {}", recipe_id)
                # Return empty list instead of raising exception for missing recipes
                return []

            _log.error("Spoonacular API HTTP error {}: {}", e.response.status_code, e)
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail="Recipe recommendation service temporarily unavailable",
            ) from e

        except httpx.RequestError as e:
            _log.error(
                "Spoonacular API request failed for recipe ID {}: {}",
                recipe_id,
                e,
            )
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Recipe recommendation service temporarily unavailable",
            ) from e

    def search_recipes_by_ingredients(
        self,
        ingredients: list[str],
        number: int = 10,
        ranking: int = 2,
    ) -> list[dict[str, Any]]:
        """Search for recipes based on ingredients using Spoonacular API.

        Args:
            ingredients: List of ingredient names to search for
            number: Number of recipes to return
            ranking: How to rank the results (1=minimize missing, 2=maximize used)

        Returns:
            List of recipes with standardized format

        Raises:
            HTTPException: If API call fails
        """
        try:
            _log.debug(
                "Searching recipes by ingredients: {} (number={})",
                ingredients,
                number,
            )

            # Spoonacular's recipe search by ingredients endpoint
            url = f"{self.base_url}/recipes/findByIngredients"

            # Join ingredients with comma
            ingredients_str = ",".join(ingredients)

            params = {
                "ingredients": ingredients_str,
                "number": min(number, 100),  # Spoonacular limit
                "ranking": ranking,
                "ignorePantry": True,  # Don't assume pantry ingredients
                "apiKey": self.api_key,
            }

            response = self.client.get(url, params=params)
            response.raise_for_status()

            recipe_list = response.json()

            _log.debug(
                "Spoonacular ingredient search successful, found {} recipes",
                len(recipe_list),
            )

            # This endpoint returns a different format, convert to standard format
            return self._convert_ingredient_search_to_standard_format(recipe_list)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == HTTPStatus.PAYMENT_REQUIRED:
                _log.error("Spoonacular API quota exceeded or payment required")
                raise HTTPException(
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                    detail=(
                        "Recipe recommendation service temporarily unavailable "
                        "due to quota limits"
                    ),
                ) from e

            _log.error("Spoonacular API HTTP error {}: {}", e.response.status_code, e)
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail="Recipe recommendation service temporarily unavailable",
            ) from e

        except httpx.RequestError as e:
            _log.error(
                "Spoonacular API request failed for ingredient search: {}",
                e,
            )
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Recipe recommendation service temporarily unavailable",
            ) from e

    def _convert_recipes_to_standard_format(
        self,
        recipes: list[Any],
    ) -> list[dict[str, Any]]:
        """Convert Spoonacular recipe objects to standardized format.

        Args:
            recipes: List of SpoonacularRecipeInfo objects

        Returns:
            List of standardized recipe dictionaries
        """
        standardized_recipes = []

        for recipe in recipes:
            # Determine the best URL to use
            recipe_url = (
                getattr(recipe, "source_url", None)
                or getattr(recipe, "spoonacular_source_url", None)
                or (
                    f"https://spoonacular.com/recipes/"
                    f"{getattr(recipe, 'title', 'recipe').replace(' ', '-')}-"
                    f"{getattr(recipe, 'id', 0)}"
                )
            )

            standardized_recipes.append(
                {
                    "recipe_name": getattr(recipe, "title", "Unknown Recipe"),
                    "url": recipe_url,
                    "image_url": getattr(recipe, "image", None),
                    "summary": getattr(recipe, "summary", None),
                    "ready_in_minutes": getattr(recipe, "ready_in_minutes", None),
                    "servings": getattr(recipe, "servings", None),
                    "source": "spoonacular",
                    "confidence_score": 0.7,  # Default for Spoonacular data
                },
            )

        return standardized_recipes

    def _convert_ingredient_search_to_standard_format(
        self,
        recipes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert ingredient search results to standardized format.

        Args:
            recipes: Raw recipe list from findByIngredients endpoint

        Returns:
            List of standardized recipe dictionaries
        """
        standardized_recipes = []

        for recipe in recipes:
            recipe_id = recipe.get("id", 0)
            title = recipe.get("title", "Unknown Recipe")

            # Generate Spoonacular URL
            recipe_url = (
                f"https://spoonacular.com/recipes/"
                f"{title.replace(' ', '-')}-{recipe_id}"
            )

            standardized_recipes.append(
                {
                    "recipe_name": title,
                    "url": recipe_url,
                    "image_url": recipe.get("image"),
                    "summary": None,  # Not provided by this endpoint
                    "ready_in_minutes": None,  # Not provided by this endpoint
                    "servings": None,  # Not provided by this endpoint
                    "source": "spoonacular",
                    # Higher score for ingredient-based matches
                    "confidence_score": 0.8,
                },
            )

        return standardized_recipes
