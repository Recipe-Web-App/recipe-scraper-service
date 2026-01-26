"""Popular recipes aggregation service.

This service fetches popular/trending recipes from multiple configurable
sources, extracts engagement metrics dynamically, normalizes scores
across sources, and caches results for efficient retrieval.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx
import orjson

from app.core.config import get_settings
from app.observability.logging import get_logger
from app.schemas.recipe import (
    PopularRecipe,
    PopularRecipesData,
    RecipeEngagementMetrics,
)
from app.services.popular.exceptions import (
    PopularRecipesFetchError,
    PopularRecipesParseError,
)
from app.services.popular.extraction import (
    extract_engagement_metrics,
    is_recipe_page,
)
from app.services.popular.llm_extraction import RecipeLinkExtractor


if TYPE_CHECKING:
    from redis.asyncio import Redis

    from app.core.config.settings import (
        PopularRecipeSourceSettings,
        PopularRecipesSettings,
    )
    from app.llm.client.protocol import LLMClientProtocol

logger = get_logger(__name__)

# Browser-like headers for fetching
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}


class PopularRecipesService:
    """Service for aggregating popular recipes from multiple sources.

    Fetches recipes from configured websites, extracts engagement metrics
    dynamically (without site-specific configuration), normalizes scores
    for fair cross-source comparison, and caches results.
    """

    def __init__(
        self,
        cache_client: Redis[bytes] | None = None,
        llm_client: LLMClientProtocol | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            cache_client: Optional Redis client for caching.
            llm_client: Optional LLM client for intelligent link extraction.
        """
        self._cache_client = cache_client
        self._llm_client = llm_client
        self._http_client: httpx.AsyncClient | None = None
        self._extractor: RecipeLinkExtractor | None = None
        self._config: PopularRecipesSettings = get_settings().scraping.popular_recipes

    async def initialize(self) -> None:
        """Initialize HTTP client and other resources."""
        self._http_client = httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=httpx.Timeout(self._config.fetch_timeout),
            follow_redirects=True,
        )

        # Initialize the recipe link extractor
        self._extractor = RecipeLinkExtractor(
            llm_client=self._llm_client,
            use_llm=self._config.use_llm_extraction,
            max_html_chars=self._config.llm_extraction_max_html_chars,
            min_confidence=self._config.llm_extraction_min_confidence,
            chunk_size=self._config.llm_extraction_chunk_size,
        )

        logger.info(
            "PopularRecipesService initialized",
            enabled=self._config.enabled,
            sources_count=len(self._config.sources),
            cache_ttl=self._config.cache_ttl,
            use_llm_extraction=self._config.use_llm_extraction,
            llm_available=self._llm_client is not None,
        )

    async def shutdown(self) -> None:
        """Close HTTP client and cleanup resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        logger.debug("PopularRecipesService shutdown")

    async def get_popular_recipes(
        self,
        limit: int = 50,
        offset: int = 0,
        count_only: bool = False,
    ) -> tuple[list[PopularRecipe], int]:
        """Get popular recipes with pagination.

        Args:
            limit: Maximum number of recipes to return.
            offset: Starting index for pagination.
            count_only: If True, return empty list with only count.

        Returns:
            Tuple of (recipes list, total count).
        """
        data = await self._get_or_refresh_cache()

        total_count = data.total_count

        if count_only:
            return [], total_count

        # Apply pagination
        recipes = data.recipes[offset : offset + limit]
        return recipes, total_count

    async def invalidate_cache(self) -> None:
        """Manually invalidate the cache.

        Forces a refresh on the next request.
        """
        if self._cache_client:
            cache_key = f"popular:{self._config.cache_key}"
            await self._cache_client.delete(cache_key)
            logger.info("Popular recipes cache invalidated")

    async def refresh_cache(self) -> PopularRecipesData:
        """Force refresh the cache by fetching fresh data.

        Unlike get_popular_recipes which checks cache first, this method
        always fetches fresh data from sources and updates the cache.
        Used by background workers to proactively refresh before expiry.

        Returns:
            Freshly fetched and cached popular recipes data.
        """
        logger.info("Force refreshing popular recipes cache")
        data = await self._fetch_all_sources()
        await self._save_to_cache(data)
        return data

    async def _get_or_refresh_cache(self) -> PopularRecipesData:
        """Get data from cache or fetch fresh data.

        Returns:
            Cached or freshly fetched popular recipes data.
        """
        # Try cache first
        cached = await self._get_from_cache()
        if cached:
            logger.debug(
                "Cache hit for popular recipes",
                total_count=cached.total_count,
            )
            return cached

        # Cache miss - fetch fresh data
        logger.info("Cache miss - fetching popular recipes from sources")
        data = await self._fetch_all_sources()

        # Save to cache
        await self._save_to_cache(data)

        return data

    async def _get_from_cache(self) -> PopularRecipesData | None:
        """Get cached data if available.

        Returns:
            Cached data or None if not found.
        """
        if not self._cache_client:
            return None

        cache_key = f"popular:{self._config.cache_key}"
        try:
            cached_bytes = await self._cache_client.get(cache_key)
            if cached_bytes:
                data = orjson.loads(cached_bytes)
                return PopularRecipesData.model_validate(data)
        except Exception:
            logger.exception("Error reading from cache")

        return None

    async def _save_to_cache(self, data: PopularRecipesData) -> None:
        """Save data to cache.

        Args:
            data: Data to cache.
        """
        if not self._cache_client:
            return

        cache_key = f"popular:{self._config.cache_key}"
        try:
            json_bytes = orjson.dumps(data.model_dump())
            await self._cache_client.setex(
                cache_key,
                self._config.cache_ttl,
                json_bytes,
            )
            logger.info(
                "Cached popular recipes",
                total_count=data.total_count,
                ttl=self._config.cache_ttl,
            )
        except Exception:
            logger.exception("Error saving to cache")

    async def _fetch_all_sources(self) -> PopularRecipesData:
        """Fetch recipes from all enabled sources concurrently.

        Returns:
            Aggregated and scored recipes data.
        """
        enabled_sources = [s for s in self._config.sources if s.enabled]

        if not enabled_sources:
            logger.warning("No enabled sources configured")
            return PopularRecipesData()

        # Limit concurrent fetches
        semaphore = asyncio.Semaphore(self._config.max_concurrent_fetches)

        async def fetch_with_semaphore(
            source: PopularRecipeSourceSettings,
        ) -> tuple[str, list[PopularRecipe] | str]:
            async with semaphore:
                try:
                    recipes = await self._fetch_source(source)
                except (PopularRecipesFetchError, PopularRecipesParseError) as e:
                    logger.warning(
                        "Failed to fetch source",
                        source=source.name,
                        url=f"{source.base_url}{source.popular_endpoint}",
                        error=str(e),
                    )
                    return source.name, str(e)
                except Exception as e:
                    logger.exception(
                        "Unexpected error fetching source", source=source.name
                    )
                    return source.name, str(e)
                else:
                    return source.name, recipes

        # Fetch all sources concurrently
        results = await asyncio.gather(
            *[fetch_with_semaphore(s) for s in enabled_sources]
        )

        # Separate successes and failures
        all_recipes: list[PopularRecipe] = []
        sources_fetched: list[str] = []
        fetch_errors: dict[str, str] = {}

        for source_name, result in results:
            if isinstance(result, list):
                all_recipes.extend(result)
                sources_fetched.append(source_name)
            else:
                fetch_errors[source_name] = result

        if not all_recipes:
            logger.warning(
                "No recipes fetched from any source",
                errors=fetch_errors,
            )
            return PopularRecipesData(
                fetch_errors=fetch_errors,
                last_updated=datetime.now(UTC).isoformat(),
            )

        # Normalize scores across all sources
        normalized_recipes = self._normalize_and_score(all_recipes)

        # Sort by score descending
        normalized_recipes.sort(key=lambda r: r.normalized_score, reverse=True)

        return PopularRecipesData(
            recipes=normalized_recipes,
            total_count=len(normalized_recipes),
            last_updated=datetime.now(UTC).isoformat(),
            sources_fetched=sources_fetched,
            fetch_errors=fetch_errors,
        )

    async def _fetch_source(
        self, source: PopularRecipeSourceSettings
    ) -> list[PopularRecipe]:
        """Fetch recipes from a single source.

        Args:
            source: Source configuration.

        Returns:
            List of recipes from the source.

        Raises:
            PopularRecipesFetchError: If HTTP request fails.
            PopularRecipesParseError: If parsing fails.
        """
        if not self._http_client:
            msg = "HTTP client not initialized"
            raise PopularRecipesFetchError(msg, source=source.name)

        url = f"{source.base_url.rstrip('/')}{source.popular_endpoint}"

        try:
            response = await self._http_client.get(url)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            msg = f"HTTP {e.response.status_code} from {url}"
            raise PopularRecipesFetchError(
                msg, source=source.name, status_code=e.response.status_code
            ) from e
        except httpx.RequestError as e:
            msg = f"Request failed for {url}: {e}"
            raise PopularRecipesFetchError(msg, source=source.name) from e

        html = response.text

        # Extract recipe links from listing page using LLM or regex fallback
        if not self._extractor:
            msg = "Extractor not initialized"
            raise PopularRecipesParseError(msg, source=source.name)

        try:
            recipe_links = await self._extractor.extract(
                html, source.base_url, source.name
            )
        except Exception as e:
            msg = f"Failed to parse recipe links: {e}"
            raise PopularRecipesParseError(msg, source=source.name) from e

        if not recipe_links:
            logger.warning(
                "No recipe links found on page",
                source=source.name,
                url=url,
            )
            return []

        # Limit links to process (fetch metrics for up to max_links_to_process)
        links_to_process = recipe_links[: self._config.max_links_to_process]

        logger.info(
            "Processing links",
            processing=len(links_to_process),
            total_links=len(recipe_links),
            source=source.name,
        )

        # Fetch individual recipe pages for metrics (with concurrency limit)
        recipes = await self._fetch_recipe_details(links_to_process, source)

        # Score recipes within this source
        scored_recipes = self._score_source_recipes(recipes, source)

        # NOW apply the per-source limit (after scoring)
        limited_recipes = scored_recipes[: source.max_recipes]

        logger.info(
            "Fetched recipes from source",
            source=source.name,
            fetched=len(recipes),
            after_scoring=len(limited_recipes),
        )

        return limited_recipes

    async def _fetch_recipe_details(
        self,
        recipe_links: list[tuple[str, str]],
        source: PopularRecipeSourceSettings,
    ) -> list[PopularRecipe]:
        """Fetch details for individual recipes.

        Args:
            recipe_links: List of (name, url) tuples.
            source: Source configuration.

        Returns:
            List of PopularRecipe with extracted metrics.
        """
        if not self._http_client:
            return []

        semaphore = asyncio.Semaphore(self._config.max_concurrent_fetches)

        async def fetch_one(rank: int, name: str, url: str) -> PopularRecipe | None:
            async with semaphore:
                metrics = RecipeEngagementMetrics()
                try:
                    response = await self._http_client.get(url)  # type: ignore[union-attr]
                    if response.is_success:
                        # Validate this is actually a recipe page
                        if not is_recipe_page(response.text):
                            logger.debug(
                                "Skipping non-recipe page",
                                url=url,
                                source=source.name,
                            )
                            return None

                        metrics = extract_engagement_metrics(response.text)
                except Exception:
                    # Log but continue - we'll use position-only scoring
                    logger.debug(
                        "Failed to fetch recipe details",
                        url=url,
                        source=source.name,
                    )

                return PopularRecipe(
                    recipe_name=name,
                    url=url,
                    source=source.name,
                    raw_rank=rank,
                    metrics=metrics,
                    normalized_score=0.0,  # Will be calculated later
                )

        # Fetch all recipe details concurrently
        tasks = [
            fetch_one(rank + 1, name, url)
            for rank, (name, url) in enumerate(recipe_links)
        ]
        results = await asyncio.gather(*tasks)

        # Filter out None results
        return [r for r in results if r is not None]

    def _score_source_recipes(
        self,
        recipes: list[PopularRecipe],
        source: PopularRecipeSourceSettings,
    ) -> list[PopularRecipe]:
        """Score and sort recipes within a single source.

        This allows applying the per-source limit AFTER scoring, so the
        best recipes are selected rather than just the first N by position.

        Args:
            recipes: List of recipes from this source.
            source: Source configuration.

        Returns:
            List of recipes sorted by score (descending).
        """
        if not recipes:
            return []

        # Calculate metric ranges for this source only
        metric_ranges = self._calculate_metric_ranges(recipes)
        max_position = max(r.raw_rank for r in recipes) if recipes else 1

        for recipe in recipes:
            recipe.normalized_score = self._calculate_score(
                metrics=recipe.metrics,
                position=recipe.raw_rank,
                max_position=max_position,
                source_weight=source.source_weight,
                metric_ranges=metric_ranges,
            )

        # Sort by score descending
        recipes.sort(key=lambda r: r.normalized_score, reverse=True)
        return recipes

    def _normalize_and_score(self, recipes: list[PopularRecipe]) -> list[PopularRecipe]:
        """Normalize metrics and calculate scores for all recipes.

        Uses min-max normalization to ensure fair comparison across sources,
        then applies weighted scoring algorithm.

        Args:
            recipes: List of recipes with raw metrics.

        Returns:
            List of recipes with normalized scores.
        """
        if not recipes:
            return []

        # Calculate min-max ranges for each metric
        metric_ranges = self._calculate_metric_ranges(recipes)

        # Get source weights
        source_weights = {s.name: s.source_weight for s in self._config.sources}

        # Calculate max position for position normalization
        max_positions = self._calculate_max_positions(recipes)

        # Calculate normalized score for each recipe
        for recipe in recipes:
            source_weight = source_weights.get(recipe.source, 1.0)
            max_pos = max_positions.get(recipe.source, len(recipes))

            recipe.normalized_score = self._calculate_score(
                metrics=recipe.metrics,
                position=recipe.raw_rank,
                max_position=max_pos,
                source_weight=source_weight,
                metric_ranges=metric_ranges,
            )

        return recipes

    def _calculate_metric_ranges(
        self, recipes: list[PopularRecipe]
    ) -> dict[str, tuple[float, float]]:
        """Calculate min-max ranges for each metric.

        Args:
            recipes: List of recipes with metrics.

        Returns:
            Dict mapping metric name to (min, max) tuple.
        """
        ranges: dict[str, tuple[float, float]] = {}

        # Rating count
        rating_counts = [
            r.metrics.rating_count
            for r in recipes
            if r.metrics.rating_count is not None
        ]
        if rating_counts:
            ranges["rating_count"] = (min(rating_counts), max(rating_counts))

        # Favorites
        favorites = [
            r.metrics.favorites for r in recipes if r.metrics.favorites is not None
        ]
        if favorites:
            ranges["favorites"] = (min(favorites), max(favorites))

        # Reviews
        reviews = [r.metrics.reviews for r in recipes if r.metrics.reviews is not None]
        if reviews:
            ranges["reviews"] = (min(reviews), max(reviews))

        return ranges

    def _calculate_max_positions(self, recipes: list[PopularRecipe]) -> dict[str, int]:
        """Calculate max position for each source.

        Args:
            recipes: List of recipes.

        Returns:
            Dict mapping source name to max position.
        """
        max_positions: dict[str, int] = {}
        for recipe in recipes:
            current_max = max_positions.get(recipe.source, 0)
            max_positions[recipe.source] = max(current_max, recipe.raw_rank)
        return max_positions

    def _calculate_score(
        self,
        metrics: RecipeEngagementMetrics,
        position: int,
        max_position: int,
        source_weight: float,
        metric_ranges: dict[str, tuple[float, float]],
    ) -> float:
        """Calculate weighted popularity score from engagement metrics.

        Formula:
        score = source_weight * weighted_average(
            rating_weight * normalized_rating,
            rating_count_weight * normalized_rating_count,
            favorites_weight * normalized_favorites,
            reviews_weight * normalized_reviews,
            position_weight * (1 - position/max_position)
        )

        Missing metrics are excluded (weights redistributed).

        Args:
            metrics: Engagement metrics for the recipe.
            position: Position on source page (1 = first).
            max_position: Maximum position from this source.
            source_weight: Weight for this source (0-1).
            metric_ranges: Min-max ranges for normalization.

        Returns:
            Normalized popularity score (0-1).
        """
        weights = self._config.scoring
        components: list[float] = []
        total_weight = 0.0

        # Rating (already 0-5, normalize to 0-1)
        if metrics.rating is not None:
            normalized_rating = metrics.rating / 5.0
            components.append(weights.rating_weight * normalized_rating)
            total_weight += weights.rating_weight

        # Rating count (min-max normalize)
        if metrics.rating_count is not None and "rating_count" in metric_ranges:
            min_val, max_val = metric_ranges["rating_count"]
            if max_val > min_val:
                normalized = (metrics.rating_count - min_val) / (max_val - min_val)
            else:
                normalized = 0.5  # All same value
            components.append(weights.rating_count_weight * normalized)
            total_weight += weights.rating_count_weight

        # Favorites (min-max normalize)
        if metrics.favorites is not None and "favorites" in metric_ranges:
            min_val, max_val = metric_ranges["favorites"]
            if max_val > min_val:
                normalized = (metrics.favorites - min_val) / (max_val - min_val)
            else:
                normalized = 0.5
            components.append(weights.favorites_weight * normalized)
            total_weight += weights.favorites_weight

        # Reviews (min-max normalize)
        if metrics.reviews is not None and "reviews" in metric_ranges:
            min_val, max_val = metric_ranges["reviews"]
            if max_val > min_val:
                normalized = (metrics.reviews - min_val) / (max_val - min_val)
            else:
                normalized = 0.5
            components.append(weights.reviews_weight * normalized)
            total_weight += weights.reviews_weight

        # Position bonus (first = 1.0, last = 0.0)
        if max_position > 0:
            position_score = 1.0 - (position - 1) / max_position
        else:
            position_score = 0.5
        components.append(weights.position_weight * position_score)
        total_weight += weights.position_weight

        # Calculate weighted average (redistribute weights for missing metrics)
        if total_weight > 0:
            raw_score = sum(components) / total_weight
        else:
            raw_score = position_score  # Fallback to position only

        return round(raw_score * source_weight, 4)
