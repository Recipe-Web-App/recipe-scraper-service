"""LLM-based recipe link extraction.

This module provides an extractor class that uses an LLM to intelligently
identify recipe links from HTML, filtering out navigation and category links.
Falls back to regex-based extraction on LLM failure.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Comment

from app.llm.exceptions import (
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
    LLMValidationError,
)
from app.llm.prompts.recipe_link_extraction import (
    ExtractedRecipeLink,
    ExtractedRecipeLinkList,
    RecipeLinkExtractionPrompt,
)
from app.observability.logging import get_logger
from app.services.popular.extraction import _resolve_url, extract_recipe_links


if TYPE_CHECKING:
    from app.llm.client.protocol import LLMClientProtocol


logger = get_logger(__name__)


class RecipeLinkExtractor:
    """Extracts recipe links from HTML using LLM with regex fallback.

    Uses an LLM to intelligently identify recipe links from HTML listing pages,
    filtering out navigation items, category pages, and user action links.
    Falls back to regex-based extraction when the LLM is unavailable or fails.
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol | None = None,
        *,
        use_llm: bool = True,
        max_html_chars: int,
        min_confidence: float,
        chunk_size: int = 50,
    ) -> None:
        """Initialize the recipe link extractor.

        Args:
            llm_client: LLM client for extraction. If None, uses regex fallback.
            use_llm: Feature flag to enable/disable LLM extraction.
            max_html_chars: Maximum HTML content size per batch.
            min_confidence: Minimum confidence threshold for including a link.
            chunk_size: Number of links per LLM batch.
        """
        self._llm_client = llm_client
        self._use_llm = use_llm and llm_client is not None
        self._prompt = RecipeLinkExtractionPrompt()
        self._max_html_chars = max_html_chars
        self._min_confidence = min_confidence
        self._chunk_size = chunk_size

    async def extract(
        self,
        html: str,
        base_url: str,
    ) -> list[tuple[str, str]]:
        """Extract recipe links from HTML.

        Attempts LLM-based extraction first, falling back to regex on failure.

        Args:
            html: Raw HTML content of the listing page.
            base_url: Base URL for resolving relative links.

        Returns:
            List of (recipe_name, full_url) tuples.
        """
        if not self._use_llm:
            logger.debug("LLM extraction disabled, using regex", base_url=base_url)
            return extract_recipe_links(html, base_url)

        try:
            return await self._extract_with_llm(html, base_url)
        except (LLMUnavailableError, LLMTimeoutError, LLMRateLimitError) as e:
            logger.warning(
                "LLM unavailable or rate limited, using regex fallback",
                error=str(e),
                base_url=base_url,
            )
            return extract_recipe_links(html, base_url)
        except LLMValidationError as e:
            logger.warning(
                "LLM response validation failed, using regex fallback",
                error=str(e),
                base_url=base_url,
            )
            return extract_recipe_links(html, base_url)
        except Exception as e:
            logger.exception(
                "Unexpected error in LLM extraction, using regex fallback",
                error=str(e),
                base_url=base_url,
            )
            return extract_recipe_links(html, base_url)

    async def _extract_with_llm(
        self,
        html: str,
        base_url: str,
    ) -> list[tuple[str, str]]:
        """Extract recipe links using the LLM with batched requests.

        Args:
            html: Raw HTML content.
            base_url: Base URL for resolving relative links.

        Returns:
            List of (recipe_name, full_url) tuples.

        Raises:
            LLMUnavailableError: If LLM service is unreachable.
            LLMTimeoutError: If LLM request times out.
            LLMValidationError: If LLM response doesn't match schema.
        """
        if self._llm_client is None:
            msg = "LLM client is None"
            raise LLMUnavailableError(msg)

        # Preprocess HTML to get all filtered links
        all_links = self._preprocess_html(html)

        if not all_links:
            logger.warning("No links found after preprocessing", base_url=base_url)
            return []

        # Split into chunks
        chunks = self._chunk_links(all_links)

        logger.info(
            "Processing %d links in %d batches",
            len(all_links),
            len(chunks),
            base_url=base_url,
        )

        # Process chunks sequentially (client handles rate limiting)
        all_results: list[ExtractedRecipeLink] = []
        failed_batches = 0
        for i, chunk in enumerate(chunks):
            try:
                result = await self._process_chunk(chunk, base_url, batch_num=i + 1)
                all_results.extend(result.recipe_links)
            except (
                LLMUnavailableError,
                LLMTimeoutError,
                LLMRateLimitError,
            ) as e:
                failed_batches += 1
                logger.warning(
                    "Batch %d/%d failed: %s",
                    i + 1,
                    len(chunks),
                    e,
                    base_url=base_url,
                )
                # Continue with other batches - return partial results

        # Log summary of batch processing
        if failed_batches > 0:
            logger.warning(
                "%d/%d batches failed, returning partial results",
                failed_batches,
                len(chunks),
                base_url=base_url,
                successful_extractions=len(all_results),
            )

        # If all batches failed, raise exception to trigger regex fallback
        if not all_results:
            logger.warning(
                "All LLM batches failed or returned empty",
                base_url=base_url,
            )
            msg = "All LLM batches failed or returned empty"
            raise LLMUnavailableError(msg)

        # Filter and process merged results
        links = self._filter_results_from_list(all_results, base_url)

        logger.info(
            "LLM extraction: %d extracted, %d after filtering",
            len(all_results),
            len(links),
            base_url=base_url,
        )

        return links

    async def _process_chunk(
        self,
        chunk_html: str,
        base_url: str,
        batch_num: int,
    ) -> ExtractedRecipeLinkList:
        """Process a single chunk of links through the LLM.

        Args:
            chunk_html: HTML string containing links for this batch.
            base_url: Base URL for context.
            batch_num: Batch number for logging.

        Returns:
            Extracted recipe links from this batch.
        """
        logger.debug(
            "Processing batch %d, %d chars",
            batch_num,
            len(chunk_html),
            base_url=base_url,
        )

        if self._llm_client is None:
            msg = "LLM client is None"
            raise LLMUnavailableError(msg)

        result = await self._llm_client.generate_structured(
            prompt=self._prompt.format(
                html_content=chunk_html,
                base_url=base_url,
            ),
            schema=ExtractedRecipeLinkList,
            system=self._prompt.system_prompt,
            options=self._prompt.get_options(),
        )

        # Handle cached results (returned as dict) vs fresh results (Pydantic model)
        if isinstance(result, dict):
            result = ExtractedRecipeLinkList(**result)

        logger.debug(
            "Batch %d extracted %d links",
            batch_num,
            len(result.recipe_links),
            base_url=base_url,
        )

        return result

    def _preprocess_html(self, html: str) -> list[str]:
        """Extract all links from HTML, filtering out navigation.

        Instead of sending full HTML containers, extracts just <a> tags
        with their text and href, plus parent class context for the LLM.

        Args:
            html: Raw HTML content.

        Returns:
            List of HTML link strings (no truncation - batching handles size).
        """
        soup = BeautifulSoup(html, "html.parser")

        # Remove non-content elements
        for tag in soup(
            [
                "script",
                "style",
                "noscript",
                "iframe",
                "svg",
                "meta",
                "link",
                "header",
                "footer",
                "nav",
            ]
        ):
            tag.decompose()

        # Remove HTML comments
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            comment.extract()

        # Navigation URL patterns to exclude
        nav_patterns = (
            "/cooking-style/",
            "/cuisines/",
            "/dishes-beverages/",
            "/everyday-cooking/",
            "/holidays/",
            "/news/",
            "/article/",
            "/about/",
            "/contact/",
            "/privacy/",
            "/terms/",
            "/subscribe/",
            "/newsletter/",
            "/login",
            "/signup",
            "/register",
            "/account/",
            "/search",
            "/tag/",
            "/category/",
            "/author/",
            "/collection/",
            "facebook.com",
            "twitter.com",
            "pinterest.com",
            "instagram.com",
            "youtube.com",
            "#",
            "javascript:",
            "mailto:",
        )

        # Extract links, filtering out navigation
        links_data: list[str] = []
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            text = self._clean_link_text(a.get_text(strip=True))

            if not text or not href or len(text) < 3:
                continue

            # Skip navigation URLs
            href_str = href if isinstance(href, str) else str(href)
            href_lower = href_str.lower()
            if any(pattern in href_lower for pattern in nav_patterns):
                continue

            # Skip generic nav text
            text_lower = text.lower()
            if text_lower in ("recipes", "home", "menu", "search", "login", "sign up"):
                continue

            # Get parent class for context
            parent = a.find_parent(["article", "div", "li", "section"])
            parent_class = ""
            if parent:
                class_attr = parent.get("class")
                if isinstance(class_attr, list):
                    parent_class = " ".join(class_attr)

            links_data.append(
                f'<a href="{href}" data-context="{parent_class}">{text}</a>'
            )

        # Return ALL links - batching will handle chunking
        return links_data

    def _chunk_links(self, links: list[str]) -> list[str]:
        """Split links into chunks for batched LLM processing.

        Args:
            links: List of HTML link strings.

        Returns:
            List of concatenated HTML strings, one per batch.
        """
        chunks: list[str] = []
        for i in range(0, len(links), self._chunk_size):
            chunk = links[i : i + self._chunk_size]
            chunk_html = "\n".join(chunk)

            # Respect max chars per chunk
            if len(chunk_html) > self._max_html_chars:
                chunk_html = chunk_html[: self._max_html_chars] + "\n<!-- truncated -->"

            chunks.append(chunk_html)

        return chunks

    # URL patterns that indicate category pages, not individual recipes
    _CATEGORY_URL_PATTERNS = (
        "/everyday-cooking/",
        "/holidays-and-events/",
        "/family-friendly/",
        "/quick-and-easy/",
        "/one-pot-meals/",
        "/sheet-pan-dinners/",
        "/comfort-food/",
        "/cookware-and-equipment/",
        "/more-meal-ideas/",
        "/main-dishes/",
    )

    # Generic link text that should be replaced with URL-derived names
    _GENERIC_LINK_TEXT = (
        "get recipe",
        "get the recipe",
        "view recipe",
        "view the recipe",
        "see recipe",
        "see the recipe",
        "read more",
        "view all",
        "go to recipe",
        "recipe",
        "click here",
        "learn more",
    )

    def _filter_results_from_list(
        self,
        recipe_links: list[ExtractedRecipeLink],
        base_url: str,
    ) -> list[tuple[str, str]]:
        """Filter and process merged LLM extraction results.

        Filters by confidence threshold, resolves URLs, deduplicates,
        and filters out category pages that the LLM incorrectly included.

        Args:
            recipe_links: List of extracted recipe links from all batches.
            base_url: Base URL for resolving relative links.

        Returns:
            Filtered list of (recipe_name, full_url) tuples.
        """
        links: list[tuple[str, str]] = []
        seen_urls: set[str] = set()

        for link in recipe_links:
            # Filter by confidence
            if link.confidence < self._min_confidence:
                logger.debug(
                    "Filtering low confidence link",
                    recipe_name=link.recipe_name,
                    confidence=link.confidence,
                    threshold=self._min_confidence,
                )
                continue

            # Resolve relative URLs
            url = _resolve_url(link.url, base_url)
            if not url:
                continue

            # Filter out category URLs
            if self._is_category_url(url):
                logger.debug("Filtering category URL: %s", url)
                continue

            # Deduplicate
            if url in seen_urls:
                continue

            # Clean and fix recipe names
            name = self._clean_link_text(link.recipe_name.strip())

            # Replace generic link text with URL-derived name
            if name.lower() in self._GENERIC_LINK_TEXT:
                name = self._extract_name_from_url(url)
                if not name:
                    continue

            # Validate recipe name
            if len(name) < 3:
                continue

            links.append((name, url))
            seen_urls.add(url)

        return links

    def _clean_link_text(self, text: str) -> str:
        """Clean link text by stripping rating/review suffixes.

        Handles cases where recipe sites concatenate rating counts
        to recipe names, e.g., "Turkey Chili2,332Ratings".

        Args:
            text: Raw link text extracted from HTML.

        Returns:
            Cleaned recipe name without rating/review suffixes.
        """
        # Strip patterns like "Turkey Chili2,332Ratings" or "Soup1,234 Reviews"
        text = re.sub(r"[\d,]+\s*Ratings?$", "", text, flags=re.IGNORECASE)
        text = re.sub(r"[\d,]+\s*Reviews?$", "", text, flags=re.IGNORECASE)
        return text.strip()

    def _is_category_url(self, url: str) -> bool:
        """Check if URL is a category page, not an individual recipe."""
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in self._CATEGORY_URL_PATTERNS)

    def _extract_name_from_url(self, url: str) -> str:
        """Extract recipe name from URL slug.

        Example: /recipes/creamy-white-chili/ -> "Creamy White Chili"
        """
        path = urlparse(url).path.rstrip("/")
        if not path:
            return ""

        # Get the last path segment (the slug)
        slug = path.split("/")[-1]
        if not slug:
            return ""

        # Convert slug to title case
        # "creamy-white-chili" -> "Creamy White Chili"
        words = slug.replace("-", " ").replace("_", " ").split()
        return " ".join(word.capitalize() for word in words)
