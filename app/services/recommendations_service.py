"""Recommendations service for generating ingredient substitutions and pairings."""

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.schemas.common.ingredient import Ingredient as IngredientSchema
from app.api.v1.schemas.common.ingredient import Quantity as QuantitySchema
from app.api.v1.schemas.common.pagination_params import PaginationParams
from app.api.v1.schemas.common.web_recipe import WebRecipe
from app.api.v1.schemas.response.pairing_suggestions_response import (
    PairingSuggestionsResponse,
)
from app.api.v1.schemas.response.recommended_substitutions_response import (
    RecommendedSubstitutionsResponse,
)
from app.core.logging import get_logger
from app.db.models.ingredient_models.ingredient import Ingredient as IngredientModel
from app.db.models.recipe_models.recipe import Recipe as RecipeModel
from app.db.models.recipe_models.recipe_ingredient import RecipeIngredient
from app.db.models.recipe_models.recipe_tag_junction import RecipeTagJunction
from app.deps.downstream_service_manager import get_downstream_service_manager
from app.utils.cache_manager import get_cache_manager

_log = get_logger(__name__)


class RecommendationsService:
    """Service for generating recipe recommendations and ingredient substitutions.

    This service provides functionality for: - Finding ingredient substitutions using
    Spoonacular API - Generating recipe pairing suggestions - Caching recommendations
    for performance - Converting between different quantity units and ratios

    Attributes:     cache_manager: Manager for caching recommendation results
    spoonacular_service: Service for Spoonacular API interactions
    """

    _MIN_SHARED_INGREDIENTS = 2

    def __init__(self) -> None:
        """Initialize the RecommendationsService with dependencies."""
        self._cache_manager = get_cache_manager()

        service_manager = get_downstream_service_manager()
        self._spoonacular_service = service_manager.get_spoonacular_service()

    def get_recommended_substitutions(
        self,
        ingredient_id: int,
        quantity: QuantitySchema | None,
        pagination: PaginationParams,
        db: Session,
    ) -> RecommendedSubstitutionsResponse:
        """Generate a list of recommended substitutions using Spoonacular API.

        Args:     ingredient_id (int): The ID of the ingredient to process.     quantity
        (Quantity): The quantity of the ingredient to process.     pagination
        (PaginationParams): Pagination params for response control.     db (Session):
        Database session for ingredient lookup.

        Returns:     RecommendedSubstitutionsResponse: Spoonacular API powered
        substitutions.

        Raises:     HTTPException: If ingredient not found or Spoonacular API
        unavailable.
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
        recommended_substitutions = (
            self._spoonacular_service.get_ingredient_substitutions(
                ingredient_name=ingredient.name,
            )
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

    async def get_pairing_suggestions(
        self,
        recipe_id: int,
        pagination: PaginationParams,
        db: Session,
    ) -> PairingSuggestionsResponse:
        """Identify suggested pairings using database and Spoonacular analysis.

        Args:     recipe_id (int): The ID of the recipe.     pagination
        (PaginationParams): Pagination params for response control.     db (Session):
        Database session for recipe lookup.

        Returns:     PairingSuggestionsResponse: The generated list of suggested
        pairings.
        """
        _log.info("Getting pairing suggestions for recipe ID {}", recipe_id)

        try:
            # Get the target recipe from database
            target_recipe = self._get_recipe_by_id(recipe_id, db)

            # Get suggestions from both database and Spoonacular
            db_suggestions = self._get_database_pairing_suggestions(target_recipe, db)
            spoonacular_suggestions = await self._get_spoonacular_pairing_suggestions(
                target_recipe,
                db,
            )

            # Combine and deduplicate results
            all_suggestions = db_suggestions + spoonacular_suggestions
            unique_suggestions = self._deduplicate_suggestions(all_suggestions)

            _log.info(
                "Generated {} unique pairing suggestions for recipe {} "
                "(DB: {}, Spoonacular: {})",
                len(unique_suggestions),
                recipe_id,
                len(db_suggestions),
                len(spoonacular_suggestions),
            )

            return PairingSuggestionsResponse.from_all(
                recipe_id,
                unique_suggestions,
                pagination,
            )

        except HTTPException:
            # Re-raise HTTP exceptions (like 404 for recipe not found)
            raise
        except SQLAlchemyError as e:
            _log.error(
                "Database error while generating pairing suggestions for recipe {}: {}",
                recipe_id,
                e,
            )
            # Return empty suggestions rather than crash
            return PairingSuggestionsResponse.from_all(recipe_id, [], pagination)
        except Exception as e:  # noqa: BLE001
            _log.error(
                "Unexpected error while generating pairing suggestions "
                "for recipe {}: {}",
                recipe_id,
                e,
            )
            # Return empty suggestions rather than crash
            return PairingSuggestionsResponse.from_all(recipe_id, [], pagination)

    def _get_database_pairing_suggestions(
        self,
        target_recipe: RecipeModel,
        db: Session,
    ) -> list[WebRecipe]:
        """Get pairing suggestions using database analysis.

        Args:     target_recipe: The target recipe to find similar recipes for     db:
        Database session

        Returns:     List of WebRecipe objects from database analysis
        """
        suggestions = []

        # Strategy 1: Database - Similar ingredients (most relevant)
        try:
            similar_recipes = self._find_recipes_with_similar_ingredients(
                target_recipe,
                db,
                limit=5,
            )
            suggestions.extend(similar_recipes)
            _log.debug(
                "Found {} recipes with similar ingredients",
                len(similar_recipes),
            )
        except SQLAlchemyError as e:
            _log.warning("Failed to find similar ingredient recipes: {}", e)

        # Strategy 2: Database - Similar tags (cuisine, course, etc.)
        try:
            tagged_recipes = self._find_recipes_with_similar_tags(
                target_recipe,
                db,
                limit=5,
            )
            suggestions.extend(tagged_recipes)
            _log.debug("Found {} recipes with similar tags", len(tagged_recipes))
        except SQLAlchemyError as e:
            _log.warning("Failed to find similar tagged recipes: {}", e)

        return suggestions

    async def _get_spoonacular_pairing_suggestions(
        self,
        target_recipe: RecipeModel,
        db: Session,
    ) -> list[WebRecipe]:
        """Get pairing suggestions using Spoonacular API.

        Args:     target_recipe: The target recipe to find similar recipes for     db:
        Database session for ingredient lookup

        Returns:     List of WebRecipe objects from Spoonacular API
        """
        suggestions = []

        try:
            # Strategy 1: Use ingredients from the recipe to search for similar recipes
            recipe_ingredients = self._get_recipe_ingredients(target_recipe, db)
            if recipe_ingredients:
                # Generate cache key based on recipe ingredients
                ingredients_key = "_".join(sorted(recipe_ingredients))
                cache_key = (
                    f"spoonacular_pairing_{target_recipe.recipe_id}_"
                    f"{hash(ingredients_key) % 1000000}"
                )

                # Try to get from cache first
                cached_suggestions = await self._cache_manager.get(cache_key)
                if cached_suggestions is not None:
                    _log.debug(
                        "Cache hit for Spoonacular pairing suggestions for recipe {}",
                        target_recipe.recipe_id,
                    )
                    # Convert cached data back to WebRecipe objects
                    # Ensure cached_suggestions is a list of dictionaries
                    if isinstance(cached_suggestions, list):
                        return [
                            WebRecipe(
                                recipe_name=item.get("recipe_name", "Unknown Recipe"),
                                url=item.get("url", ""),
                            )
                            for item in cached_suggestions
                            if isinstance(item, dict)
                        ]

                    _log.warning(
                        "Invalid cached data format for recipe {}, ignoring cache",
                        target_recipe.recipe_id,
                    )

                try:
                    suggestions = (
                        self._spoonacular_service.search_recipes_by_ingredients(
                            ingredients=recipe_ingredients,
                            limit=100,  # Use maximum limit
                        )
                    )
                    _log.debug(
                        "Found {} Spoonacular recipes based on ingredients",
                        len(suggestions),
                    )

                    # Cache results - convert WebRecipe objects for JSON serialization
                    if suggestions:
                        cache_data = [
                            {"recipe_name": recipe.recipe_name, "url": recipe.url}
                            for recipe in suggestions
                        ]
                        try:
                            await self._cache_manager.set(
                                cache_key,
                                cache_data,
                                expiry_hours=24,
                            )
                            _log.debug(
                                "Cached {} Spoonacular pairing suggestions "
                                "for recipe {}",
                                len(cache_data),
                                target_recipe.recipe_id,
                            )
                        except (OSError, ValueError) as cache_error:
                            _log.warning(
                                "Failed to cache Spoonacular pairing suggestions "
                                "for recipe {}: {}",
                                target_recipe.recipe_id,
                                cache_error,
                            )

                except HTTPException as e:
                    _log.warning("Spoonacular ingredient search failed: {}", e.detail)

        except Exception as e:  # noqa: BLE001
            _log.warning(
                "Unexpected error getting Spoonacular pairing suggestions: {}",
                e,
            )

        return suggestions

    def _get_recipe_ingredients(
        self,
        recipe: RecipeModel,
        db: Session,
    ) -> list[str]:
        """Get ingredient names for a recipe.

        Args:     recipe: Recipe model     db: Database session

        Returns:     List of ingredient names
        """
        try:
            # Get ingredients for the recipe
            ingredients = (
                db.query(RecipeIngredient)
                .filter(RecipeIngredient.recipe_id == recipe.recipe_id)
                .all()
            )

            # Extract ingredient names using list comprehension
            ingredient_names = [
                recipe_ingredient.ingredient.name
                for recipe_ingredient in ingredients
                if recipe_ingredient.ingredient and recipe_ingredient.ingredient.name
            ]

        except SQLAlchemyError as e:
            _log.warning(
                "Failed to get ingredients for recipe {}: {}",
                recipe.recipe_id,
                e,
            )
            return []
        else:
            return ingredient_names

    def _get_recipe_by_id(self, recipe_id: int, db: Session) -> RecipeModel:
        """Get recipe from database by ID.

        Args:     recipe_id: The ID of the recipe to retrieve     db: Database session

        Returns:     RecipeModel: The recipe model

        Raises:     HTTPException: If recipe not found
        """
        recipe = (
            db.query(RecipeModel).filter(RecipeModel.recipe_id == recipe_id).first()
        )
        if not recipe:
            raise HTTPException(status_code=404, detail=f"Recipe {recipe_id} not found")
        return recipe

    def _find_recipes_with_similar_ingredients(
        self,
        target_recipe: RecipeModel,
        db: Session,
        limit: int = 10,
    ) -> list[WebRecipe]:
        """Find recipes that share ingredients with the target recipe.

        Args:     target_recipe: The target recipe to find similar recipes for     db:
        Database session     limit: Maximum number of recipes to return

        Returns:     List of WebRecipe objects with similar ingredients
        """
        # Get ingredients for the target recipe
        target_ingredients_query = db.query(RecipeIngredient.ingredient_id).filter(
            RecipeIngredient.recipe_id == target_recipe.recipe_id,
        )

        # Find recipes with overlapping ingredients
        similar_recipes = (
            db.query(
                RecipeModel,
                func.count(RecipeIngredient.ingredient_id).label("shared_count"),
            )
            .join(RecipeIngredient)
            .filter(
                RecipeIngredient.ingredient_id.in_(target_ingredients_query),
                RecipeModel.recipe_id
                != target_recipe.recipe_id,  # Exclude target recipe
            )
            .group_by(RecipeModel.recipe_id)
            .having(
                func.count(RecipeIngredient.ingredient_id)
                >= self._MIN_SHARED_INGREDIENTS,
            )  # At least _MIN_SHARED_INGREDIENTS shared ingredients
            .order_by(func.count(RecipeIngredient.ingredient_id).desc())
            .limit(limit)
            .all()
        )

        return [
            WebRecipe(
                recipe_name=recipe.title,
                url=recipe.origin_url
                or f"https://sous-chef-proxy.local/recipes/{recipe.recipe_id}",
            )
            for recipe, _ in similar_recipes
        ]

    def _find_recipes_with_similar_tags(
        self,
        target_recipe: RecipeModel,
        db: Session,
        limit: int = 10,
    ) -> list[WebRecipe]:
        """Find recipes that share tags with the target recipe.

        Args:     target_recipe: The target recipe to find similar recipes for     db:
        Database session     limit: Maximum number of recipes to return

        Returns:     List of WebRecipe objects with similar tags
        """
        # Get tags for the target recipe
        target_tags_query = db.query(RecipeTagJunction.tag_id).filter(
            RecipeTagJunction.recipe_id == target_recipe.recipe_id,
        )

        # Find recipes with overlapping tags
        similar_recipes = (
            db.query(
                RecipeModel,
                func.count(RecipeTagJunction.tag_id).label("shared_count"),
            )
            .join(RecipeTagJunction)
            .filter(
                RecipeTagJunction.tag_id.in_(target_tags_query),
                RecipeModel.recipe_id
                != target_recipe.recipe_id,  # Exclude target recipe
            )
            .group_by(RecipeModel.recipe_id)
            .having(func.count(RecipeTagJunction.tag_id) >= 1)  # At least 1 shared tag
            .order_by(func.count(RecipeTagJunction.tag_id).desc())
            .limit(limit)
            .all()
        )

        return [
            WebRecipe(
                recipe_name=recipe.title,
                url=recipe.origin_url
                or f"https://sous-chef-proxy.local/recipes/{recipe.recipe_id}",
            )
            for recipe, _ in similar_recipes
        ]

    def _deduplicate_suggestions(self, suggestions: list[WebRecipe]) -> list[WebRecipe]:
        """Remove duplicate recipe suggestions based on name similarity.

        Args:     suggestions: List of WebRecipe suggestions

        Returns:     List of unique WebRecipe suggestions
        """
        seen_names = set()
        unique_suggestions = []

        for suggestion in suggestions:
            # Normalize name for comparison
            normalized_name = suggestion.recipe_name.lower().strip()

            if normalized_name not in seen_names:
                seen_names.add(normalized_name)
                unique_suggestions.append(suggestion)

        return unique_suggestions
