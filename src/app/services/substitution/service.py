"""Substitution service for LLM-powered ingredient substitution recommendations.

Provides methods for:
- Single ingredient substitution lookup
- Redis caching with 7-day TTL
- Pagination at response time
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import orjson

from app.cache.redis import get_cache_client
from app.database.repositories.nutrition import NutritionRepository
from app.llm.exceptions import (
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
    LLMValidationError,
)
from app.llm.prompts.substitution import (
    IngredientSubstitutionPrompt,
    SubstitutionListResult,
)
from app.observability.logging import get_logger
from app.schemas.enums import IngredientUnit
from app.schemas.ingredient import Ingredient, Quantity
from app.schemas.recommendations import (
    ConversionRatio,
    IngredientSubstitution,
    RecommendedSubstitutionsResponse,
)
from app.services.substitution.constants import (
    SUBSTITUTION_CACHE_KEY_PREFIX,
    SUBSTITUTION_CACHE_TTL_SECONDS,
)
from app.services.substitution.exceptions import (
    LLMGenerationError,
)


if TYPE_CHECKING:
    from redis.asyncio import Redis

    from app.llm.client.protocol import LLMClientProtocol

logger = get_logger(__name__)


class SubstitutionService:
    """Service for generating ingredient substitution recommendations.

    Orchestrates:
    1. Redis cache lookups for cached substitutions
    2. LLM-based generation for new substitutions
    3. Pagination at response time
    4. Transformation to API response schemas

    Cache Strategy:
    - Cache key: "substitution:{ingredient_name_normalized}"
    - TTL: 7 days
    - Caches raw LLM output (SubstitutionListResult), not paginated responses
    - Pagination applied at response time based on limit/offset
    """

    def __init__(
        self,
        cache_client: Redis[bytes] | None = None,
        llm_client: LLMClientProtocol | None = None,
        nutrition_repository: NutritionRepository | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            cache_client: Optional Redis client for caching.
            llm_client: Optional LLM client for generation.
            nutrition_repository: Optional repository for ingredient lookups.
        """
        self._cache_client = cache_client
        self._llm_client = llm_client
        self._nutrition_repository = nutrition_repository
        self._prompt = IngredientSubstitutionPrompt()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize service resources.

        Called during application startup. Sets up repository if not injected.
        """
        if self._cache_client is None:
            try:
                self._cache_client = get_cache_client()
            except RuntimeError:
                logger.warning("Redis not available, caching disabled")

        if self._nutrition_repository is None:
            self._nutrition_repository = NutritionRepository()

        self._initialized = True
        logger.info("SubstitutionService initialized")

    async def shutdown(self) -> None:
        """Cleanup service resources.

        Called during application shutdown.
        """
        logger.info("SubstitutionService shutdown")

    async def get_substitutions(
        self,
        ingredient_id: str,
        quantity: Quantity | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> RecommendedSubstitutionsResponse | None:
        """Get substitution recommendations for an ingredient.

        Args:
            ingredient_id: Ingredient name or ID.
            quantity: Optional quantity for context.
            limit: Maximum results to return.
            offset: Number of results to skip.

        Returns:
            Substitution recommendations, or None if ingredient not found.

        Raises:
            IngredientNotFoundError: If ingredient cannot be resolved.
            LLMGenerationError: If LLM fails to generate substitutions.
        """
        if not self._initialized:
            logger.error("SubstitutionService not initialized")
            return None

        if self._llm_client is None:
            logger.error("LLM client not available")
            return None

        # Resolve ingredient name and get food_group context
        ingredient_name = ingredient_id
        food_group: str | None = None

        if self._nutrition_repository:
            nutrition_data = await self._nutrition_repository.get_by_ingredient_name(
                ingredient_id
            )
            if nutrition_data is None:
                # Try fuzzy match
                nutrition_data = (
                    await self._nutrition_repository.get_by_ingredient_name_fuzzy(
                        ingredient_id
                    )
                )

            if nutrition_data:
                ingredient_name = nutrition_data.ingredient_name
                food_group = nutrition_data.food_group
                logger.debug(
                    "Resolved ingredient",
                    query=ingredient_id,
                    resolved_name=ingredient_name,
                    food_group=food_group,
                )

        # Get substitutions (from cache or generate)
        substitutions = await self._get_or_generate_substitutions(
            ingredient_name=ingredient_name,
            food_group=food_group,
            quantity=quantity,
        )

        if substitutions is None:
            return None

        # Apply pagination
        total_count = len(substitutions.substitutions)
        paginated_subs = substitutions.substitutions[offset : offset + limit]

        # Transform to API response
        return self._transform_to_response(
            ingredient_name=ingredient_name,
            substitutions=paginated_subs,
            quantity=quantity,
            limit=limit,
            offset=offset,
            total_count=total_count,
        )

    async def _get_or_generate_substitutions(
        self,
        ingredient_name: str,
        food_group: str | None,
        quantity: Quantity | None,
    ) -> SubstitutionListResult | None:
        """Get substitutions from cache or generate via LLM.

        Args:
            ingredient_name: Resolved ingredient name.
            food_group: Optional food group for context.
            quantity: Optional quantity for context.

        Returns:
            Substitution list result, or None on failure.

        Raises:
            LLMGenerationError: If LLM fails to generate.
        """
        # Check cache first
        cached = await self._get_from_cache(ingredient_name)
        if cached is not None:
            logger.debug("Cache hit", ingredient=ingredient_name)
            return cached

        # Cache miss - generate via LLM
        logger.debug("Cache miss, generating via LLM", ingredient=ingredient_name)
        result = await self._generate_substitutions(
            ingredient_name=ingredient_name,
            food_group=food_group,
            quantity=quantity,
        )

        # Cache the result
        if result is not None:
            await self._save_to_cache(ingredient_name, result)

        return result

    async def _generate_substitutions(
        self,
        ingredient_name: str,
        food_group: str | None,
        quantity: Quantity | None,
    ) -> SubstitutionListResult | None:
        """Generate substitutions using LLM.

        Args:
            ingredient_name: Ingredient name.
            food_group: Optional food group context.
            quantity: Optional quantity context.

        Returns:
            Generated substitutions or None on failure.

        Raises:
            LLMGenerationError: If LLM fails to generate.
        """
        if self._llm_client is None:
            logger.error("LLM client not available for generation")
            return None

        # Build prompt kwargs
        prompt_kwargs: dict[str, Any] = {"ingredient_name": ingredient_name}
        if food_group:
            prompt_kwargs["food_group"] = food_group
        if quantity:
            prompt_kwargs["quantity"] = {
                "amount": quantity.amount,
                "measurement": quantity.measurement.value,
            }

        try:
            result = await self._llm_client.generate_structured(
                prompt=self._prompt.format(**prompt_kwargs),
                schema=SubstitutionListResult,
                system=self._prompt.system_prompt,
                options=self._prompt.get_options(),
                context=f"substitution:{ingredient_name}",
            )

            # Handle cached results (returned as dict) vs fresh results (Pydantic model)
            if isinstance(result, dict):
                result = SubstitutionListResult(**result)

            logger.info(
                "Generated substitutions",
                ingredient=ingredient_name,
                count=len(result.substitutions),
            )
        except (LLMUnavailableError, LLMTimeoutError) as e:
            logger.warning(
                "LLM unavailable for substitution generation",
                ingredient=ingredient_name,
                error=str(e),
            )
            raise LLMGenerationError(
                message=f"LLM unavailable: {e}",
                ingredient=ingredient_name,
                cause=e,
            ) from e
        except LLMRateLimitError as e:
            logger.warning(
                "LLM rate limited",
                ingredient=ingredient_name,
                error=str(e),
            )
            raise LLMGenerationError(
                message=f"LLM rate limited: {e}",
                ingredient=ingredient_name,
                cause=e,
            ) from e
        except LLMValidationError as e:
            logger.warning(
                "LLM response validation failed",
                ingredient=ingredient_name,
                error=str(e),
            )
            raise LLMGenerationError(
                message=f"LLM response invalid: {e}",
                ingredient=ingredient_name,
                cause=e,
            ) from e
        except Exception as e:
            logger.exception(
                "Unexpected error during substitution generation",
                ingredient=ingredient_name,
            )
            raise LLMGenerationError(
                message=f"Unexpected error: {e}",
                ingredient=ingredient_name,
                cause=e,
            ) from e
        else:
            return result

    # =========================================================================
    # Cache Operations
    # =========================================================================

    async def _get_from_cache(
        self, ingredient_name: str
    ) -> SubstitutionListResult | None:
        """Get substitution data from cache.

        Args:
            ingredient_name: Ingredient name.

        Returns:
            SubstitutionListResult or None if not cached.
        """
        if self._cache_client is None:
            return None

        cache_key = self._make_cache_key(ingredient_name)

        try:
            cached_bytes = await self._cache_client.get(cache_key)
            if cached_bytes:
                data = orjson.loads(cached_bytes)
                return SubstitutionListResult.model_validate(data)
        except Exception:
            logger.exception("Cache read error", key=cache_key)

        return None

    async def _save_to_cache(
        self, ingredient_name: str, data: SubstitutionListResult
    ) -> None:
        """Save substitution data to cache.

        Args:
            ingredient_name: Ingredient name.
            data: SubstitutionListResult to cache.
        """
        if self._cache_client is None:
            return

        cache_key = self._make_cache_key(ingredient_name)

        try:
            json_bytes = orjson.dumps(data.model_dump(mode="json"))
            await self._cache_client.setex(
                cache_key,
                SUBSTITUTION_CACHE_TTL_SECONDS,
                json_bytes,
            )
            logger.debug("Cached substitution data", key=cache_key)
        except Exception:
            logger.exception("Cache write error", key=cache_key)

    def _make_cache_key(self, ingredient_name: str) -> str:
        """Create cache key for an ingredient.

        Args:
            ingredient_name: Ingredient name.

        Returns:
            Cache key string.
        """
        # Normalize name for consistent caching
        normalized = ingredient_name.lower().strip()
        return f"{SUBSTITUTION_CACHE_KEY_PREFIX}:{normalized}"

    # =========================================================================
    # Transformation
    # =========================================================================

    def _transform_to_response(
        self,
        ingredient_name: str,
        substitutions: list[Any],
        quantity: Quantity | None,
        limit: int,
        offset: int,
        total_count: int,
    ) -> RecommendedSubstitutionsResponse:
        """Transform LLM output to API response.

        Args:
            ingredient_name: Original ingredient name.
            substitutions: Paginated list of SubstitutionResult objects.
            quantity: Optional original quantity.
            limit: Requested limit.
            offset: Requested offset.
            total_count: Total number of substitutions available.

        Returns:
            API response schema.
        """
        # Build original ingredient
        original_ingredient = Ingredient(
            ingredient_id=None,
            name=ingredient_name,
            quantity=quantity,
        )

        # Transform substitutions
        transformed_subs: list[IngredientSubstitution] = []
        for sub in substitutions:
            # Calculate adjusted quantity if original quantity provided
            adjusted_quantity: Quantity | None = None
            if quantity:
                adjusted_amount = quantity.amount * sub.ratio
                # Try to use the same unit, fall back to sub's measurement
                try:
                    unit = IngredientUnit(sub.measurement.value)
                except ValueError:
                    unit = quantity.measurement
                adjusted_quantity = Quantity(amount=adjusted_amount, measurement=unit)

            transformed_subs.append(
                IngredientSubstitution(
                    ingredient=sub.ingredient,
                    quantity=adjusted_quantity,
                    conversion_ratio=ConversionRatio(
                        ratio=sub.ratio,
                        measurement=IngredientUnit(sub.measurement.value),
                    ),
                )
            )

        return RecommendedSubstitutionsResponse(
            ingredient=original_ingredient,
            recommended_substitutions=transformed_subs,
            limit=limit,
            offset=offset,
            count=total_count,
        )
