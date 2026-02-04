"""Pairings service for LLM-powered recipe pairing recommendations.

Provides methods for:
- Recipe pairing lookup based on flavor profiles and cuisine types
- Redis caching with 24-hour TTL
- Pagination at response time
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import orjson

from app.cache.redis import get_cache_client
from app.llm.exceptions import (
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
    LLMValidationError,
)
from app.llm.prompts.pairings import (
    PairingListResult,
    PairingResult,
    RecipePairingPrompt,
)
from app.observability.logging import get_logger
from app.schemas.ingredient import WebRecipe
from app.schemas.recommendations import PairingSuggestionsResponse
from app.services.pairings.constants import (
    PAIRINGS_CACHE_KEY_PREFIX,
    PAIRINGS_CACHE_TTL_SECONDS,
)
from app.services.pairings.exceptions import (
    LLMGenerationError,
)


if TYPE_CHECKING:
    from redis.asyncio import Redis

    from app.llm.client.protocol import LLMClientProtocol

logger = get_logger(__name__)


@dataclass
class RecipeContext:
    """Context extracted from recipe for LLM prompt.

    Contains the essential information needed to generate
    relevant pairing suggestions.
    """

    recipe_id: int
    title: str
    description: str | None
    ingredients: list[str]


class PairingsService:
    """Service for generating recipe pairing recommendations.

    Orchestrates:
    1. Redis cache lookups for cached pairings
    2. LLM-based generation for new pairings
    3. Pagination at response time
    4. Transformation to API response schemas

    Cache Strategy:
    - Cache key: "pairing:{recipe_id}"
    - TTL: 24 hours
    - Caches raw LLM output (PairingListResult), not paginated responses
    - Pagination applied at response time based on limit/offset
    """

    def __init__(
        self,
        cache_client: Redis[bytes] | None = None,
        llm_client: LLMClientProtocol | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            cache_client: Optional Redis client for caching.
            llm_client: Optional LLM client for generation.
        """
        self._cache_client = cache_client
        self._llm_client = llm_client
        self._prompt = RecipePairingPrompt()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize service resources.

        Called during application startup.
        """
        if self._cache_client is None:
            try:
                self._cache_client = get_cache_client()
            except RuntimeError:
                logger.warning("Redis not available, caching disabled")

        self._initialized = True
        logger.info("PairingsService initialized")

    async def shutdown(self) -> None:
        """Cleanup service resources.

        Called during application shutdown.
        """
        logger.info("PairingsService shutdown")

    async def get_pairings(
        self,
        context: RecipeContext,
        limit: int = 50,
        offset: int = 0,
    ) -> PairingSuggestionsResponse | None:
        """Get pairing recommendations for a recipe.

        Args:
            context: Recipe context with title, description, ingredients.
            limit: Maximum results to return.
            offset: Number of results to skip.

        Returns:
            Pairing suggestions, or None if service unavailable.

        Raises:
            LLMGenerationError: If LLM fails to generate pairings.
        """
        if not self._initialized:
            logger.error("PairingsService not initialized")
            return None

        if self._llm_client is None:
            logger.error("LLM client not available")
            return None

        # Get pairings (from cache or generate)
        pairings = await self._get_or_generate_pairings(context)

        if pairings is None:
            return None

        # Apply pagination
        total_count = len(pairings.pairings)
        paginated_pairings = pairings.pairings[offset : offset + limit]

        # Transform to API response
        return self._transform_to_response(
            recipe_id=context.recipe_id,
            pairings=paginated_pairings,
            limit=limit,
            offset=offset,
            total_count=total_count,
        )

    async def _get_or_generate_pairings(
        self,
        context: RecipeContext,
    ) -> PairingListResult | None:
        """Get pairings from cache or generate via LLM.

        Args:
            context: Recipe context for generation.

        Returns:
            Pairing list result, or None on failure.

        Raises:
            LLMGenerationError: If LLM fails to generate.
        """
        # Check cache first
        cached = await self._get_from_cache(context.recipe_id)
        if cached is not None:
            logger.debug("Cache hit", recipe_id=context.recipe_id)
            return cached

        # Cache miss - generate via LLM
        logger.debug("Cache miss, generating via LLM", recipe_id=context.recipe_id)
        result = await self._generate_pairings(context)

        # Cache the result
        if result is not None:
            await self._save_to_cache(context.recipe_id, result)

        return result

    async def _generate_pairings(
        self,
        context: RecipeContext,
    ) -> PairingListResult | None:
        """Generate pairings using LLM.

        Args:
            context: Recipe context for prompt generation.

        Returns:
            Generated pairings or None on failure.

        Raises:
            LLMGenerationError: If LLM fails to generate.
        """
        if self._llm_client is None:
            logger.error("LLM client not available for generation")
            return None

        try:
            result = await self._llm_client.generate_structured(
                prompt=self._prompt.format(
                    title=context.title,
                    description=context.description,
                    ingredients=context.ingredients,
                ),
                schema=PairingListResult,
                system=self._prompt.system_prompt,
                options=self._prompt.get_options(),
                context=f"pairing:{context.recipe_id}",
            )

            # Handle cached results (returned as dict) vs fresh results (Pydantic model)
            if isinstance(result, dict):
                result = PairingListResult(**result)

            logger.info(
                "Generated pairings",
                recipe_id=context.recipe_id,
                count=len(result.pairings),
            )
        except (LLMUnavailableError, LLMTimeoutError) as e:
            logger.warning(
                "LLM unavailable for pairing generation",
                recipe_id=context.recipe_id,
                error=str(e),
            )
            raise LLMGenerationError(
                message=f"LLM unavailable: {e}",
                recipe_id=context.recipe_id,
                cause=e,
            ) from e
        except LLMRateLimitError as e:
            logger.warning(
                "LLM rate limited",
                recipe_id=context.recipe_id,
                error=str(e),
            )
            raise LLMGenerationError(
                message=f"LLM rate limited: {e}",
                recipe_id=context.recipe_id,
                cause=e,
            ) from e
        except LLMValidationError as e:
            logger.warning(
                "LLM response validation failed",
                recipe_id=context.recipe_id,
                error=str(e),
            )
            raise LLMGenerationError(
                message=f"LLM response invalid: {e}",
                recipe_id=context.recipe_id,
                cause=e,
            ) from e
        except Exception as e:
            logger.exception(
                "Unexpected error during pairing generation",
                recipe_id=context.recipe_id,
            )
            raise LLMGenerationError(
                message=f"Unexpected error: {e}",
                recipe_id=context.recipe_id,
                cause=e,
            ) from e
        else:
            return result

    # =========================================================================
    # Cache Operations
    # =========================================================================

    async def _get_from_cache(self, recipe_id: int) -> PairingListResult | None:
        """Get pairing data from cache.

        Args:
            recipe_id: Recipe ID.

        Returns:
            PairingListResult or None if not cached.
        """
        if self._cache_client is None:
            return None

        cache_key = self._make_cache_key(recipe_id)

        try:
            cached_bytes = await self._cache_client.get(cache_key)
            if cached_bytes:
                data = orjson.loads(cached_bytes)
                return PairingListResult.model_validate(data)
        except Exception:
            logger.exception("Cache read error", key=cache_key)

        return None

    async def _save_to_cache(self, recipe_id: int, data: PairingListResult) -> None:
        """Save pairing data to cache.

        Args:
            recipe_id: Recipe ID.
            data: PairingListResult to cache.
        """
        if self._cache_client is None:
            return

        cache_key = self._make_cache_key(recipe_id)

        try:
            json_bytes = orjson.dumps(data.model_dump(mode="json"))
            await self._cache_client.setex(
                cache_key,
                PAIRINGS_CACHE_TTL_SECONDS,
                json_bytes,
            )
            logger.debug("Cached pairing data", key=cache_key)
        except Exception:
            logger.exception("Cache write error", key=cache_key)

    def _make_cache_key(self, recipe_id: int) -> str:
        """Create cache key for a recipe.

        Args:
            recipe_id: Recipe ID.

        Returns:
            Cache key string.
        """
        return f"{PAIRINGS_CACHE_KEY_PREFIX}:{recipe_id}"

    # =========================================================================
    # Transformation
    # =========================================================================

    def _transform_to_response(
        self,
        recipe_id: int,
        pairings: list[PairingResult],
        limit: int,
        offset: int,
        total_count: int,
    ) -> PairingSuggestionsResponse:
        """Transform LLM output to API response.

        Args:
            recipe_id: Original recipe ID.
            pairings: Paginated list of PairingResult objects.
            limit: Requested limit.
            offset: Requested offset.
            total_count: Total number of pairings available.

        Returns:
            API response schema.
        """
        # Transform pairings to WebRecipe format
        web_recipes = [
            WebRecipe(recipe_name=pairing.recipe_name, url=pairing.url)
            for pairing in pairings
        ]

        return PairingSuggestionsResponse(
            recipe_id=recipe_id,
            pairing_suggestions=web_recipes,
            limit=limit,
            offset=offset,
            count=total_count,
        )
