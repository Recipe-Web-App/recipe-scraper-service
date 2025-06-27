"""Recommendations service for generating ingredient substitutions and pairings."""

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.v1.schemas.common.ingredient import Ingredient as IngredientSchema
from app.api.v1.schemas.common.ingredient import Quantity as QuantitySchema
from app.api.v1.schemas.common.pagination_params import PaginationParams
from app.api.v1.schemas.common.web_recipe import WebRecipe
from app.api.v1.schemas.response.pairing_suggestions_response import (
    PairingSuggestionsResponse,
)
from app.api.v1.schemas.response.recommended_substitutions_response import (
    ConversionRatio,
    IngredientSubstitution,
    RecommendedSubstitutionsResponse,
)
from app.core.logging import get_logger
from app.db.models.ingredient_models.ingredient import Ingredient as IngredientModel
from app.deps.downstream_service_manager import get_downstream_service_manager
from app.enums.ingredient_unit_enum import IngredientUnitEnum
from app.exceptions.custom_exceptions import SubstitutionNotFoundError
from app.utils.cache_manager import CacheManager

_log = get_logger(__name__)


class RecommendationsService:
    """Service for generating recipe recommendations and ingredient substitutions.

    This service provides functionality for:
    - Finding ingredient substitutions using Spoonacular API
    - Generating recipe pairing suggestions
    - Caching recommendations for performance
    - Converting between different quantity units and ratios

    Attributes:
        cache_manager: Manager for caching recommendation results
        spoonacular_service: Service for Spoonacular API interactions
    """

    def __init__(self) -> None:
        """Initialize the RecommendationsService with dependencies."""
        self.cache_manager = CacheManager()

        service_manager = get_downstream_service_manager()
        self.spoonacular_service = service_manager.get_spoonacular_service()

    def get_recommended_substitutions(
        self,
        ingredient_id: int,
        quantity: QuantitySchema | None,
        pagination: PaginationParams,
        db: Session,
    ) -> RecommendedSubstitutionsResponse:
        """Generate a list of recommended substitutions using Spoonacular API.

        Args:
            ingredient_id (int): The ID of the ingredient to process.
            quantity (Quantity): The quantity of the ingredient to process.
            pagination (PaginationParams): Pagination params for response control.
            db (Session): Database session for ingredient lookup.

        Returns:
            RecommendedSubstitutionsResponse: Spoonacular API powered substitutions.

        Raises:
            HTTPException: If ingredient not found or Spoonacular API unavailable.
        """
        quantity_str = (
            "Quantity = " + f"{quantity.amount} {quantity.measurement}"
            if quantity
            else "None"
        )
        _log.info(
            "Getting Spoonacular-powered substitutions for Ingredient ID {} "
            "({} | limit={} | offset={} | count_only={})",
            ingredient_id,
            quantity_str,
            pagination.limit,
            pagination.offset,
            pagination.count_only,
        )

        # Look up the ingredient name from the database
        ingredient = (
            db.query(IngredientModel)
            .filter(
                IngredientModel.ingredient_id == ingredient_id,
            )
            .first()
        )

        if not ingredient:
            _log.warning("Ingredient with ID {} not found", ingredient_id)
            raise HTTPException(
                status_code=404,
                detail=f"Ingredient with ID {ingredient_id} not found",
            )

        # Get Spoonacular substitutions
        recommended_substitutions = self._get_spoonacular_substitutions(
            ingredient_name=ingredient.name,
        )
        _log.info("Generated substitutions: {}", recommended_substitutions)

        response = RecommendedSubstitutionsResponse.from_all(
            IngredientSchema(
                ingredient_id=ingredient_id,
                name=ingredient.name,
                quantity=quantity,
            ),
            recommended_substitutions,
            pagination,
        )
        _log.info(
            "Generated RecommendedSubstitutionsResponse: {}",
            response,
        )

        return response

    def get_pairing_suggestions(
        self,
        recipe_id: int,
        pagination: PaginationParams,
    ) -> PairingSuggestionsResponse:
        """Identify suggested pairings for the given recipe.

        Args:
            recipe_id (int): The ID of the ingredient.
            pagination (PaginationParams): Pagination params for response control.

        Returns:
            PairingSuggestionsResponse: The generated list of suggested pairings.
        """
        pairing_suggestions = [
            WebRecipe(
                recipe_name="Dummy Recipe 1",
                url="https://some-url.com/dummy-recipe-1",
            ),
            WebRecipe(
                recipe_name="Dummy Recipe 2",
                url="https://some-url.com/dummy-recipe-2",
            ),
            WebRecipe(
                recipe_name="Dummy Recipe 3",
                url="https://some-url.com/dummy-recipe-3",
            ),
            WebRecipe(
                recipe_name="Dummy Recipe 4",
                url="https://some-url.com/dummy-recipe-4",
            ),
            WebRecipe(
                recipe_name="Dummy Recipe 5",
                url="https://some-url.com/dummy-recipe-5",
            ),
            WebRecipe(
                recipe_name="Dummy Recipe 6",
                url="https://some-url.com/dummy-recipe-6",
            ),
            WebRecipe(
                recipe_name="Dummy Recipe 7",
                url="https://some-url.com/dummy-recipe-7",
            ),
            WebRecipe(
                recipe_name="Dummy Recipe 8",
                url="https://some-url.com/dummy-recipe-8",
            ),
            WebRecipe(
                recipe_name="Dummy Recipe 9",
                url="https://some-url.com/dummy-recipe-9",
            ),
            WebRecipe(
                recipe_name="Dummy Recipe 10",
                url="https://some-url.com/dummy-recipe-10",
            ),
        ]

        return PairingSuggestionsResponse.from_all(
            recipe_id,
            pairing_suggestions,
            pagination,
        )

    def _get_spoonacular_substitutions(
        self,
        ingredient_name: str,
    ) -> list[IngredientSubstitution]:
        """Get substitutions using Spoonacular API.

        Args:
            ingredient_name: Name of the ingredient to substitute
            quantity: Optional quantity information for context

        Returns:
            List of ingredient substitutions from Spoonacular
        """
        # Check cache first
        cache_key = f"substitutions_{ingredient_name.lower().replace(' ', '_')}"
        cached_substitutions = self.cache_manager.get(cache_key)

        if cached_substitutions:
            _log.info("Using cached substitutions for ingredient '{}'", ingredient_name)
            if isinstance(cached_substitutions, list):
                return self._parse_cached_substitutions(cached_substitutions)
            _log.warning("Unexpected cache format, regenerating substitutions")

        # Get substitutions from Spoonacular
        try:
            _log.debug(
                "Getting substitutions from Spoonacular for '{}'",
                ingredient_name,
            )

            provider_data = self.spoonacular_service.get_ingredient_substitutes(
                ingredient_name,
            )
            substitutions = self._parse_provider_response(provider_data)

            # Cache the results for 24 hours
            cache_data = [
                {
                    "ingredient": sub_data["substitute_ingredient"],
                    "conversion_ratio": sub_data.get("conversion_ratio", 1.0),
                    "source": "spoonacular",
                }
                for sub_data in provider_data
            ]
            self.cache_manager.set(cache_key, cache_data, expiry_hours=24)

            _log.info(
                "Successfully got {} substitutions from Spoonacular for '{}'",
                len(substitutions),
                ingredient_name,
            )

        except SubstitutionNotFoundError as e:
            _log.warning(
                "Spoonacular could not find substitutes for '{}': {}",
                ingredient_name,
                e.get_reason() if hasattr(e, "get_reason") else str(e),
            )
            raise HTTPException(
                status_code=404,
                detail=f"No substitutes available for ingredient: {ingredient_name}",
            ) from e

        except HTTPException:
            # Let HTTPExceptions from Spoonacular service bubble up
            raise

        except (ConnectionError, TimeoutError) as e:
            _log.error(
                "Network error from Spoonacular for '{}': {}",
                ingredient_name,
                e,
            )
            raise HTTPException(
                status_code=503,
                detail="Ingredient substitution service temporarily unavailable",
            ) from e
        else:
            return substitutions

    def _parse_cached_substitutions(
        self,
        cached_data: list[dict[str, Any]],
    ) -> list[IngredientSubstitution]:
        """Parse cached substitution data into IngredientSubstitution objects.

        Args:
            cached_data: Cached substitution data
            quantity: Current quantity for conversion calculations

        Returns:
            List of ingredient substitutions with adjusted quantities
        """
        substitutions = []
        for sub_data in cached_data:
            # Extract conversion ratio data
            conversion_ratio_data = sub_data.get("conversion_ratio", {})

            # Calculate adjusted quantity using the ratio value
            ratio_value = conversion_ratio_data.get("ratio")

            # Create ConversionRatio object for the response
            conversion_ratio = ConversionRatio(
                ratio=ratio_value,
                measurement=conversion_ratio_data.get(
                    "measurement",
                    IngredientUnitEnum.UNIT,
                ),
            )

            substitutions.append(
                IngredientSubstitution(
                    ingredient=sub_data["ingredient"],
                    conversion_ratio=conversion_ratio,
                ),
            )

        return substitutions

    def _parse_provider_response(
        self,
        provider_data: list[dict[str, Any]],
    ) -> list[IngredientSubstitution]:
        """Parse provider response into IngredientSubstitution objects.

        Args:
            provider_data: Response from any provider service
            original_quantity: Original quantity for conversion calculations

        Returns:
            List of parsed ingredient substitutions
        """
        substitutions = []
        for sub_data in provider_data:
            # Extract conversion ratio data
            conversion_ratio_data = sub_data.get("conversion_ratio", {})

            # Calculate adjusted quantity using the ratio value
            ratio_value = conversion_ratio_data.get("ratio", 1.0)

            # Create ConversionRatio object for the response
            conversion_ratio = ConversionRatio(
                ratio=ratio_value,
                measurement=conversion_ratio_data.get(
                    "measurement",
                    IngredientUnitEnum.UNIT,
                ),
            )

            substitutions.append(
                IngredientSubstitution(
                    ingredient=sub_data["substitute_ingredient"],
                    conversion_ratio=conversion_ratio,
                ),
            )

        return substitutions
