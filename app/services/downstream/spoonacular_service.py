"""Spoonacular API service for ingredient substitutions.

This service provides ingredient substitution functionality using the Spoonacular API,
which offers a reliable database of cooking ingredient substitutes.
"""

import re
from http import HTTPStatus
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config.config import settings
from app.core.logging import get_logger
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
        # Check if Spoonacular returned a failure response
        if data.get("status") == "failure":
            error_message = data.get("message", "Unknown error from Spoonacular API")
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

        # Handle different response formats from Spoonacular
        substitute_list = data.get("substitutes", [])

        if isinstance(substitute_list, list):
            for substitute in substitute_list:
                if isinstance(substitute, str):
                    # Simple string format
                    parsed = self._parse_substitute_string(substitute)
                    if parsed:
                        substitutes.append(parsed)
                elif isinstance(substitute, dict):
                    # Dict format with more details
                    substitutes.append(
                        {
                            "substitute_ingredient": substitute.get(
                                "name",
                                substitute.get("substitute", ""),
                            ),
                            "conversion_ratio": self._extract_ratio_from_description(
                                substitute.get("description", ""),
                            ),
                            "notes": substitute.get("description", ""),
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

    def _parse_substitute_string(self, substitute_str: str) -> dict[str, Any] | None:
        """Parse a substitute string into structured data.

        Args:
            substitute_str: Raw substitute string from API

        Returns:
            Structured substitute information or None if parsing fails
        """
        if not substitute_str or not substitute_str.strip():
            return None

        # Clean up the string
        substitute_str = substitute_str.strip()

        # Extract ratio information if present
        ratio = self._extract_ratio_from_description(substitute_str)

        # Extract the main ingredient name (before any ratio/description)
        ingredient_name = substitute_str.split(" (")[0].split(" -")[0].strip()

        return {
            "substitute_ingredient": ingredient_name,
            "conversion_ratio": ratio,
            "notes": substitute_str,
            "confidence_score": 0.8,
        }

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
