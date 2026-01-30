"""Allergen service for retrieving allergen information.

Implements tiered lookup: Database → Open Food Facts → LLM inference.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import orjson

from app.clients.open_food_facts.client import OpenFoodFactsClient
from app.database.repositories.allergen import AllergenData, AllergenRepository
from app.observability.logging import get_logger
from app.schemas.allergen import (
    AllergenDataSource,
    AllergenInfo,
    AllergenPresenceType,
    IngredientAllergenResponse,
    RecipeAllergenResponse,
)
from app.schemas.enums import Allergen
from app.services.allergen.constants import (
    ALLERGEN_CACHE_KEY_PREFIX,
    ALLERGEN_CACHE_TTL_SECONDS,
    CONFIDENCE_OPEN_FOOD_FACTS,
)


if TYPE_CHECKING:
    from redis.asyncio import Redis

    from app.schemas.ingredient import Ingredient

logger = get_logger(__name__)


class AllergenService:
    """Service for retrieving allergen information.

    Orchestrates:
    1. Redis cache lookups
    2. PostgreSQL database queries via AllergenRepository
    3. Open Food Facts API fallback
    4. LLM inference for remaining gaps (placeholder)
    5. Allergen aggregation for recipes
    """

    def __init__(
        self,
        cache_client: Redis[bytes] | None = None,
        repository: AllergenRepository | None = None,
        off_client: OpenFoodFactsClient | None = None,
    ) -> None:
        """Initialize the allergen service.

        Args:
            cache_client: Redis client for caching.
            repository: Database repository for allergen data.
            off_client: Open Food Facts API client.
        """
        self._cache = cache_client
        self._repository = repository
        self._off_client = off_client
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize service dependencies."""
        if self._repository is None:
            self._repository = AllergenRepository()
        if self._off_client is None:
            self._off_client = OpenFoodFactsClient(cache_client=self._cache)
            await self._off_client.initialize()
        self._initialized = True
        logger.info("AllergenService initialized")

    async def shutdown(self) -> None:
        """Cleanup service resources."""
        if self._off_client is not None:
            await self._off_client.shutdown()
        self._initialized = False
        logger.info("AllergenService shutdown")

    async def get_ingredient_allergens(
        self,
        name: str,
    ) -> IngredientAllergenResponse | None:
        """Get allergen information for a single ingredient.

        Uses tiered lookup: Cache → DB → Open Food Facts → LLM.

        Args:
            name: Ingredient name to look up.

        Returns:
            IngredientAllergenResponse or None if not found.
        """
        if not self._initialized:
            logger.warning("AllergenService not initialized")
            return None

        # Tier 0: Cache lookup
        cached = await self._get_from_cache(name)
        if cached is not None:
            logger.debug("Cache hit for allergen data", ingredient=name)
            return cached

        # Tier 1: Database lookup (exact then fuzzy)
        db_result = await self._get_from_database(name)
        if db_result:
            await self._cache_result(name, db_result)
            return db_result

        # Tier 2: Open Food Facts API
        off_result = await self._get_from_open_food_facts(name)
        if off_result:
            await self._cache_result(name, off_result)
            return off_result

        # Tier 3: LLM inference (placeholder)
        llm_result = await self._get_from_llm(name)
        if llm_result:
            await self._cache_result(name, llm_result)
            return llm_result

        logger.info("No allergen data found", ingredient=name)
        return None

    async def get_recipe_allergens(
        self,
        ingredients: list[Ingredient],
        include_details: bool = False,
    ) -> RecipeAllergenResponse:
        """Get aggregated allergen information for a recipe.

        Args:
            ingredients: List of recipe ingredients.
            include_details: Whether to include per-ingredient breakdown.

        Returns:
            RecipeAllergenResponse with aggregated allergens.
        """
        ingredient_results: dict[str, IngredientAllergenResponse] = {}
        missing: list[int] = []

        # Fetch allergens for each ingredient
        for ingredient in ingredients:
            if not ingredient.name:
                if ingredient.ingredient_id:
                    missing.append(ingredient.ingredient_id)
                continue

            result = await self.get_ingredient_allergens(ingredient.name)
            if result:
                ingredient_results[ingredient.name] = result
            elif ingredient.ingredient_id:
                missing.append(ingredient.ingredient_id)

        # Aggregate allergens
        contains, may_contain, all_allergens = self._aggregate_allergens(
            list(ingredient_results.values())
        )

        return RecipeAllergenResponse(
            contains=contains,
            may_contain=may_contain,
            allergens=all_allergens,
            ingredient_details=ingredient_results if include_details else None,
            missing_ingredients=missing,
        )

    async def _get_from_cache(
        self,
        name: str,
    ) -> IngredientAllergenResponse | None:
        """Try to get allergen data from cache."""
        if not self._cache:
            return None

        try:
            key = self._make_cache_key(name)
            data = await self._cache.get(key)
            if data:
                return IngredientAllergenResponse.model_validate(orjson.loads(data))
        except Exception:
            logger.exception("Cache lookup failed")
        return None

    async def _get_from_database(
        self,
        name: str,
    ) -> IngredientAllergenResponse | None:
        """Get allergen data from database."""
        if self._repository is None:
            return None

        # Try exact match first
        data = await self._repository.get_by_ingredient_name(name)
        if not data:
            # Try fuzzy match
            data = await self._repository.get_by_ingredient_name_fuzzy(name)

        if not data:
            return None

        return self._transform_db_to_response(data)

    async def _get_from_open_food_facts(
        self,
        name: str,
    ) -> IngredientAllergenResponse | None:
        """Get allergen data from Open Food Facts API."""
        if not self._off_client:
            return None

        product = await self._off_client.search_by_name(name)
        if not product or not product.allergens:
            return None

        allergens = [
            AllergenInfo(
                allergen=a.allergen,
                presence_type=AllergenPresenceType(a.presence_type),
                confidence_score=CONFIDENCE_OPEN_FOOD_FACTS,
                source_notes=f"From Open Food Facts: {product.product_name}",
            )
            for a in product.allergens
        ]

        return IngredientAllergenResponse(
            ingredient_name=name,
            allergens=allergens,
            data_source=AllergenDataSource.OPEN_FOOD_FACTS,
            overall_confidence=CONFIDENCE_OPEN_FOOD_FACTS,
        )

    async def _get_from_llm(
        self,
        name: str,
    ) -> IngredientAllergenResponse | None:
        """Get allergen data via LLM inference.

        Placeholder for Tier 3 - returns None for now.
        """
        logger.debug("LLM inference not yet implemented", ingredient=name)
        return None

    async def _cache_result(
        self,
        name: str,
        result: IngredientAllergenResponse,
    ) -> None:
        """Cache allergen result."""
        if not self._cache:
            return

        try:
            key = self._make_cache_key(name)
            data = orjson.dumps(result.model_dump(mode="json"))
            await self._cache.setex(key, ALLERGEN_CACHE_TTL_SECONDS, data)
            logger.debug("Cached allergen data", key=key)
        except Exception:
            logger.exception("Cache write failed")

    def _make_cache_key(self, name: str) -> str:
        """Create cache key for an ingredient."""
        normalized = name.lower().strip()
        return f"{ALLERGEN_CACHE_KEY_PREFIX}:{normalized}"

    def _transform_db_to_response(
        self,
        data: list[AllergenData],
    ) -> IngredientAllergenResponse:
        """Transform database data to response schema."""
        if not data:
            return IngredientAllergenResponse()

        first = data[0]
        allergens = [
            AllergenInfo(
                allergen=Allergen(d.allergen_type),
                presence_type=AllergenPresenceType(d.presence_type),
                confidence_score=float(d.confidence_score),
                source_notes=d.source_notes,
            )
            for d in data
        ]

        return IngredientAllergenResponse(
            ingredient_id=first.ingredient_id,
            ingredient_name=first.ingredient_name,
            usda_food_description=first.usda_food_description,
            allergens=allergens,
            data_source=AllergenDataSource(first.data_source),
            overall_confidence=float(first.profile_confidence),
        )

    def _aggregate_allergens(
        self,
        ingredient_allergens: list[IngredientAllergenResponse],
    ) -> tuple[list[Allergen], list[Allergen], list[AllergenInfo]]:
        """Aggregate allergens across multiple ingredients.

        Returns:
            Tuple of (contains, may_contain, all_allergens).
        """
        contains: set[Allergen] = set()
        may_contain: set[Allergen] = set()
        all_allergens: dict[Allergen, AllergenInfo] = {}

        for resp in ingredient_allergens:
            for allergen_info in resp.allergens:
                # Handle both Allergen enum and string values
                # (schema may serialize to strings via use_enum_values=True)
                raw_allergen = allergen_info.allergen
                a = (
                    Allergen(raw_allergen)
                    if isinstance(raw_allergen, str)
                    else raw_allergen
                )

                if allergen_info.presence_type == AllergenPresenceType.CONTAINS:
                    contains.add(a)
                else:
                    may_contain.add(a)

                # Keep highest confidence for each allergen
                if a not in all_allergens or (allergen_info.confidence_score or 0) > (
                    all_allergens[a].confidence_score or 0
                ):
                    all_allergens[a] = allergen_info

        # Remove from may_contain if in contains
        may_contain -= contains

        return (
            sorted(contains, key=lambda x: x.value),
            sorted(may_contain, key=lambda x: x.value),
            list(all_allergens.values()),
        )
