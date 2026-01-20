"""Recipe scraper service.

This module provides the main recipe scraping functionality using:
1. recipe-scrapers library as the primary extractor (400+ supported sites)
2. JSON-LD structured data as a fallback
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
import orjson
from recipe_scrapers import WebsiteNotImplementedError, scrape_html

from app.core.config import get_settings
from app.observability.logging import get_logger
from app.services.scraping.exceptions import (
    RecipeNotFoundError,
    ScrapingFetchError,
    ScrapingParseError,
    ScrapingTimeoutError,
)
from app.services.scraping.jsonld import extract_recipe_from_jsonld
from app.services.scraping.models import ScrapedRecipe


if TYPE_CHECKING:
    from collections.abc import Callable

    from redis.asyncio import Redis


logger = get_logger(__name__)


class RecipeScraperService:
    """Service for scraping recipe data from URLs.

    Uses recipe-scrapers library as the primary extraction method,
    with JSON-LD structured data as a fallback for unsupported sites.

    Example:
        ```python
        service = RecipeScraperService()
        await service.initialize()

        recipe = await service.scrape("https://example.com/recipe")
        print(recipe.title, recipe.ingredients)

        await service.shutdown()
        ```
    """

    def __init__(
        self,
        cache_client: Redis[bytes] | None = None,
    ) -> None:
        """Initialize the scraper service.

        Args:
            cache_client: Optional Redis client for caching scraped recipes.
        """
        self._settings = get_settings()
        self._cache_client = cache_client
        self._http_client: httpx.AsyncClient | None = None

    async def initialize(self) -> None:
        """Initialize HTTP client and other resources."""
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._settings.scraping.fetch_timeout),
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,image/webp,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.5",
            },
        )
        logger.info("RecipeScraperService initialized")

    async def shutdown(self) -> None:
        """Release resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        logger.debug("RecipeScraperService shutdown")

    async def scrape(
        self,
        url: str,
        *,
        skip_cache: bool = False,
    ) -> ScrapedRecipe:
        """Scrape recipe data from a URL.

        Attempts extraction using recipe-scrapers first, then falls back
        to JSON-LD parsing if the site is unsupported.

        Args:
            url: The recipe URL to scrape.
            skip_cache: If True, bypass cache and fetch fresh data.

        Returns:
            ScrapedRecipe containing the extracted data.

        Raises:
            ScrapingFetchError: If fetching the URL fails.
            ScrapingTimeoutError: If the request times out.
            RecipeNotFoundError: If no recipe data found on the page.
            ScrapingParseError: If parsing the recipe data fails.
        """
        # Check cache first
        if (
            not skip_cache
            and self._cache_client
            and self._settings.scraping.cache_enabled
        ):
            cached = await self._get_from_cache(url)
            if cached:
                logger.debug("Cache hit for recipe URL", url=url)
                return cached

        # Fetch HTML
        html = await self._fetch_html(url)

        # Try recipe-scrapers first
        recipe = await self._extract_with_recipe_scrapers(url, html)

        if recipe is None:
            # Fall back to JSON-LD
            logger.debug("Falling back to JSON-LD extraction", url=url)
            recipe = await self._extract_with_jsonld(url, html)

        if recipe is None:
            logger.warning("No recipe data found", url=url)
            error_msg = f"No recipe data found at {url}"
            raise RecipeNotFoundError(error_msg)

        # Cache the result
        if self._cache_client and self._settings.scraping.cache_enabled:
            await self._save_to_cache(url, recipe)

        return recipe

    async def _fetch_html(self, url: str) -> str:
        """Fetch HTML content from URL.

        Args:
            url: The URL to fetch.

        Returns:
            HTML content as string.

        Raises:
            ScrapingFetchError: If the request fails.
            ScrapingTimeoutError: If the request times out.
        """
        if not self._http_client:
            msg = "Service not initialized. Call initialize() first."
            raise RuntimeError(msg)

        try:
            response = await self._http_client.get(url)
            response.raise_for_status()

        except httpx.TimeoutException as e:
            logger.warning("Request timed out", url=url, error=str(e))
            error_msg = f"Request timed out: {url}"
            raise ScrapingTimeoutError(error_msg) from e

        except httpx.HTTPStatusError as e:
            logger.warning(
                "HTTP error fetching URL",
                url=url,
                status_code=e.response.status_code,
            )
            error_msg = f"HTTP {e.response.status_code} fetching {url}"
            raise ScrapingFetchError(error_msg) from e

        except httpx.RequestError as e:
            logger.warning("Request error fetching URL", url=url, error=str(e))
            error_msg = f"Failed to fetch {url}: {e}"
            raise ScrapingFetchError(error_msg) from e

        else:
            html: str = response.text
            return html

    async def _extract_with_recipe_scrapers(
        self,
        url: str,
        html: str,
    ) -> ScrapedRecipe | None:
        """Extract recipe using recipe-scrapers library.

        Args:
            url: Original URL (needed for site detection).
            html: HTML content.

        Returns:
            ScrapedRecipe if extraction succeeds, None if site unsupported.

        Raises:
            ScrapingParseError: If parsing fails for a supported site.
        """
        try:
            scraper = scrape_html(html, org_url=url)

            # Extract all available fields
            recipe = ScrapedRecipe(
                title=scraper.title(),
                description=self._safe_call_str_field(scraper.description),
                servings=self._safe_call_str_field(scraper.yields),
                prep_time=self._safe_call_int_field(scraper.prep_time),
                cook_time=self._safe_call_int_field(scraper.cook_time),
                total_time=self._safe_call_int_field(scraper.total_time),
                ingredients=scraper.ingredients() or [],
                instructions=self._parse_instructions(scraper.instructions_list()),
                image_url=self._safe_call_str_field(scraper.image),
                source_url=url,
                author=self._safe_call_str_field(scraper.author),
                cuisine=self._safe_call_str_field(scraper.cuisine),
                category=self._safe_call_str_field(scraper.category),
                keywords=self._parse_keywords(self._safe_call_str(scraper.keywords)),
                yields=self._safe_call_str_field(scraper.yields),
            )

            logger.info(
                "Successfully extracted recipe with recipe-scrapers",
                url=url,
                title=recipe.title,
            )

        except WebsiteNotImplementedError:
            logger.debug("Site not supported by recipe-scrapers", url=url)
            return None

        except Exception as e:
            # recipe-scrapers can raise various exceptions for malformed data
            logger.warning(
                "recipe-scrapers extraction failed",
                url=url,
                error=str(e),
            )
            error_msg = f"Failed to parse recipe from {url}: {e}"
            raise ScrapingParseError(error_msg) from e

        else:
            return recipe

    async def _extract_with_jsonld(
        self,
        url: str,
        html: str,
    ) -> ScrapedRecipe | None:
        """Extract recipe using JSON-LD structured data.

        Args:
            url: Original URL.
            html: HTML content.

        Returns:
            ScrapedRecipe if extraction succeeds, None otherwise.
        """
        try:
            return extract_recipe_from_jsonld(html, url)
        except Exception as e:
            logger.debug(
                "JSON-LD extraction failed",
                url=url,
                error=str(e),
            )
            return None

    def _safe_call_str_field(self, func: Callable[[], Any]) -> str | None:
        """Safely call a scraper method expecting string result.

        Args:
            func: Method to call.

        Returns:
            String value or None if it fails or is empty.
        """
        try:
            result = func()
        except Exception:
            return None
        else:
            if result is None:
                return None
            if isinstance(result, str):
                return result if result else None
            return str(result) if result else None

    def _safe_call_int_field(self, func: Callable[[], Any]) -> int | None:
        """Safely call a scraper method expecting integer result.

        Args:
            func: Method to call.

        Returns:
            Integer value or None if it fails.
        """
        try:
            result = func()
        except Exception:
            return None
        else:
            if result is None:
                return None
            if isinstance(result, int):
                return result
            # Try to convert to int
            try:
                return int(result)
            except (ValueError, TypeError):
                return None

    def _safe_call_str(self, func: Callable[[], Any]) -> str | list[str] | None:
        """Safely call a scraper method expecting string/list result.

        Args:
            func: Method to call.

        Returns:
            String, list of strings, or None if it fails.
        """
        try:
            result = func()
            if result is None:
                return None
            if isinstance(result, list | str):
                return result
            return str(result)
        except Exception:
            return None

    def _parse_instructions(self, instructions: list[str] | None) -> list[str]:
        """Parse and clean instruction list.

        Args:
            instructions: Raw instructions list.

        Returns:
            Cleaned list of non-empty instructions.
        """
        if not instructions:
            return []
        return [inst.strip() for inst in instructions if inst and inst.strip()]

    def _parse_keywords(self, keywords: str | list[str] | None) -> list[str]:
        """Parse keywords into a list.

        Args:
            keywords: Keywords as string (comma-separated) or list.

        Returns:
            List of keywords.
        """
        if not keywords:
            return []
        if isinstance(keywords, list):
            return [k.strip() for k in keywords if k and k.strip()]
        return [k.strip() for k in keywords.split(",") if k.strip()]

    async def _get_from_cache(self, url: str) -> ScrapedRecipe | None:
        """Get cached recipe data.

        Args:
            url: Recipe URL as cache key.

        Returns:
            Cached ScrapedRecipe or None.
        """
        if not self._cache_client:
            return None

        try:
            cache_key = f"recipe:scraped:{url}"
            data = await self._cache_client.get(cache_key)
            if data:
                return ScrapedRecipe.model_validate(orjson.loads(data))
        except Exception as e:
            logger.debug("Cache read failed", url=url, error=str(e))
        return None

    async def _save_to_cache(self, url: str, recipe: ScrapedRecipe) -> None:
        """Save recipe to cache.

        Args:
            url: Recipe URL as cache key.
            recipe: Recipe data to cache.
        """
        if not self._cache_client:
            return

        try:
            cache_key = f"recipe:scraped:{url}"
            await self._cache_client.set(
                cache_key,
                orjson.dumps(recipe.model_dump()),
                ex=self._settings.scraping.cache_ttl,
            )
            logger.debug("Cached scraped recipe", url=url)
        except Exception as e:
            logger.debug("Cache write failed", url=url, error=str(e))
