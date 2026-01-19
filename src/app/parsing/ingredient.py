"""Ingredient parser using LLM for normalization.

This module provides a service class for parsing raw ingredient strings
into structured data suitable for the Recipe Management Service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.llm.exceptions import (
    LLMTimeoutError,
    LLMUnavailableError,
    LLMValidationError,
)
from app.llm.prompts import (
    IngredientParsingPrompt,
    ParsedIngredient,
    ParsedIngredientList,
)
from app.observability.logging import get_logger
from app.parsing.exceptions import (
    IngredientParsingError,
    IngredientParsingTimeoutError,
    IngredientParsingValidationError,
)


if TYPE_CHECKING:
    from app.llm.client.protocol import LLMClientProtocol


logger = get_logger(__name__)


class IngredientParser:
    """Service for parsing raw ingredient strings into structured data.

    Uses an LLM to normalize ingredient strings, extracting:
    - Ingredient name (normalized)
    - Quantity (as decimal)
    - Unit (standardized enum)
    - Optional flag
    - Notes (preparation notes, size descriptors, etc.)

    Example:
        ```python
        parser = IngredientParser(llm_client)
        ingredients = await parser.parse_batch(
            [
                "2 cups all-purpose flour, sifted",
                "1/2 tsp salt",
                "3 large eggs",
            ]
        )
        # Returns list of ParsedIngredient objects
        ```
    """

    def __init__(self, llm_client: LLMClientProtocol) -> None:
        """Initialize the ingredient parser.

        Args:
            llm_client: LLM client for generating structured output.
        """
        self._llm_client = llm_client
        self._prompt = IngredientParsingPrompt()

    async def parse_batch(
        self,
        ingredients: list[str],
        *,
        skip_cache: bool = False,
    ) -> list[ParsedIngredient]:
        """Parse a batch of raw ingredient strings.

        Args:
            ingredients: List of raw ingredient strings to parse.
            skip_cache: If True, bypass LLM cache for this request.

        Returns:
            List of ParsedIngredient objects in the same order as input.

        Raises:
            IngredientParsingError: If parsing fails.
            IngredientParsingTimeoutError: If LLM request times out.
            IngredientParsingValidationError: If LLM output doesn't match schema.
        """
        if not ingredients:
            return []

        logger.debug(
            "Parsing ingredient batch",
            count=len(ingredients),
            skip_cache=skip_cache,
        )

        try:
            result = await self._llm_client.generate_structured(
                prompt=self._prompt.format(ingredients=ingredients),
                schema=ParsedIngredientList,
                system=self._prompt.system_prompt,
                options=self._prompt.get_options(),
                skip_cache=skip_cache,
            )

        except IngredientParsingError:
            # Re-raise our own exceptions as-is
            raise

        except LLMTimeoutError as e:
            logger.warning("Ingredient parsing timed out", error=str(e))
            raise IngredientParsingTimeoutError(str(e)) from e

        except LLMValidationError as e:
            logger.warning("Ingredient parsing validation failed", error=str(e))
            raise IngredientParsingValidationError(str(e)) from e

        except LLMUnavailableError as e:
            logger.warning("LLM unavailable for ingredient parsing", error=str(e))
            error_msg = f"LLM service unavailable: {e}"
            raise IngredientParsingError(error_msg) from e

        except Exception as e:
            logger.exception("Unexpected error during ingredient parsing")
            error_msg = f"Failed to parse ingredients: {e}"
            raise IngredientParsingError(error_msg) from e

        # Validate output count matches input (outside try to satisfy TRY301)
        if len(result.ingredients) != len(ingredients):
            logger.warning(
                "Ingredient count mismatch",
                input_count=len(ingredients),
                output_count=len(result.ingredients),
            )
            msg = (
                f"Expected {len(ingredients)} parsed ingredients, "
                f"got {len(result.ingredients)}"
            )
            raise IngredientParsingValidationError(msg)

        logger.debug(
            "Successfully parsed ingredients",
            count=len(result.ingredients),
        )
        return result.ingredients

    async def parse_single(
        self,
        ingredient: str,
        *,
        skip_cache: bool = False,
    ) -> ParsedIngredient:
        """Parse a single ingredient string.

        Convenience method for parsing a single ingredient.

        Args:
            ingredient: Raw ingredient string to parse.
            skip_cache: If True, bypass LLM cache for this request.

        Returns:
            ParsedIngredient object.

        Raises:
            IngredientParsingError: If parsing fails.
        """
        results = await self.parse_batch([ingredient], skip_cache=skip_cache)
        return results[0]
