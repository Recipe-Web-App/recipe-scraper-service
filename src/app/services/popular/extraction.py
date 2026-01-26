"""Dynamic engagement metrics extraction from HTML.

This module extracts engagement metrics (rating, rating_count, favorites, reviews)
from recipe pages without site-specific configuration using:
1. JSON-LD structured data (schema.org/Recipe) - most reliable
2. Microdata (itemprop attributes) - fallback
3. Common HTML patterns (class/id heuristics) - last resort

All fields are optional - returns None for any metric not found.
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from app.observability.logging import get_logger
from app.schemas.recipe import RecipeEngagementMetrics


logger = get_logger(__name__)


# =============================================================================
# Main Extraction Functions
# =============================================================================


def extract_engagement_metrics(html: str) -> RecipeEngagementMetrics:
    """Extract engagement metrics dynamically from HTML.

    Extraction priority (first successful source wins for each metric):
    1. JSON-LD structured data (schema.org/Recipe aggregateRating)
    2. Microdata (itemprop attributes)
    3. Common HTML patterns (class/id heuristics)

    Args:
        html: Raw HTML content of the recipe page.

    Returns:
        RecipeEngagementMetrics with any found values (all fields optional).
    """
    metrics = RecipeEngagementMetrics()

    # 1. Try JSON-LD first (most reliable)
    jsonld_data = _extract_jsonld_recipe(html)
    if jsonld_data:
        _extract_from_jsonld(jsonld_data, metrics)

    # 2. Try microdata for missing values
    soup = BeautifulSoup(html, "html.parser")
    _extract_from_microdata(soup, metrics)

    # 3. Fallback to HTML patterns for any still-missing values
    _extract_from_html_patterns(soup, metrics)

    return metrics


def is_recipe_page(html: str) -> bool:
    """Check if a page contains Recipe schema.org data.

    Uses JSON-LD and microdata detection to identify actual recipe pages.
    Category pages typically use CollectionPage or ItemList schema instead.

    Args:
        html: Raw HTML content of the page.

    Returns:
        True if page appears to be a recipe page, False otherwise.
    """
    # Check for Recipe JSON-LD (most reliable)
    jsonld_recipe = _extract_jsonld_recipe(html)
    if jsonld_recipe:
        return True

    # Check for Recipe microdata
    soup = BeautifulSoup(html, "lxml")
    recipe_itemtype = soup.find(
        attrs={"itemtype": lambda x: x is not None and "Recipe" in str(x)}
    )
    if recipe_itemtype:
        return True

    # Fallback: check for recipe content structure
    # (ingredients list + instructions = likely a recipe)
    has_ingredients = soup.find(
        attrs={"class": lambda x: x is not None and "ingredient" in str(x).lower()}
    )
    has_instructions = soup.find(
        attrs={
            "class": lambda x: x is not None
            and any(
                kw in str(x).lower()
                for kw in ["instruction", "direction", "step", "method"]
            )
        }
    )

    return bool(has_ingredients and has_instructions)


def extract_recipe_links(html: str, base_url: str) -> list[tuple[str, str]]:
    """Extract recipe links from a listing page.

    Looks for links that appear to be recipe URLs based on common patterns.

    Args:
        html: HTML content of the listing page.
        base_url: Base URL for resolving relative links.

    Returns:
        List of (recipe_name, full_url) tuples.
    """
    soup = BeautifulSoup(html, "html.parser")
    recipes: list[tuple[str, str]] = []
    seen_urls: set[str] = set()

    # Generic link text that should be replaced with URL-derived names
    generic_link_text = {
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
    }

    def get_name_from_url(url: str) -> str | None:
        """Extract recipe name from URL slug."""
        path = urlparse(url).path.rstrip("/")
        if not path:
            return None
        slug = path.split("/")[-1]
        if not slug or len(slug) < 3:
            return None
        words = slug.replace("-", " ").replace("_", " ").split()
        return " ".join(word.capitalize() for word in words)

    def finalize_name(name: str | None, url: str) -> str | None:
        """Finalize recipe name, replacing generic text with URL-derived name."""
        if not name:
            return get_name_from_url(url)
        if name.lower() in generic_link_text:
            return get_name_from_url(url)
        return name

    # Common patterns for recipe links
    # Look for links within article/card containers
    containers = soup.find_all(
        ["article", "div", "li"],
        class_=re.compile(r"recipe|card|item|result|listing|entry", re.IGNORECASE),
    )

    for container in containers:
        link = container.find("a", href=True)
        if link and _is_recipe_link(link):
            href = link.get("href")
            url = _resolve_url(str(href) if href else "", base_url)
            if url and url not in seen_urls:
                name = finalize_name(_extract_recipe_name(link, container), url)
                if name and len(name) > 3:
                    recipes.append((name, url))
                    seen_urls.add(url)

    # Fallback: look for any recipe-like links if no containers found
    if not recipes:
        for link in soup.find_all("a", href=True):
            if _is_recipe_link(link):
                href = link.get("href")
                url = _resolve_url(str(href) if href else "", base_url)
                if url and url not in seen_urls:
                    name = finalize_name(_extract_link_text(link), url)
                    if name and len(name) > 3:  # Filter out very short text
                        recipes.append((name, url))
                        seen_urls.add(url)

    return recipes


# =============================================================================
# JSON-LD Extraction
# =============================================================================


def _extract_jsonld_recipe(html: str) -> dict[str, Any] | None:
    """Find and extract Recipe schema from JSON-LD blocks.

    Args:
        html: Raw HTML content.

    Returns:
        Recipe JSON-LD dictionary if found, None otherwise.
    """
    # Find all JSON-LD script blocks
    pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
    matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

    for match in matches:
        try:
            data = json.loads(match.strip())
            recipe = _find_recipe_in_jsonld(data)
            if recipe:
                return recipe
        except json.JSONDecodeError:
            continue

    return None


def _find_recipe_in_jsonld(data: Any) -> dict[str, Any] | None:
    """Find Recipe schema in JSON-LD data structure.

    Handles various formats:
    - Direct Recipe object
    - @graph array containing Recipe
    - Array of objects

    Args:
        data: Parsed JSON-LD data.

    Returns:
        Recipe dictionary if found, None otherwise.
    """
    if isinstance(data, dict):
        schema_type = data.get("@type", "")
        if isinstance(schema_type, list):
            schema_type = " ".join(schema_type)
        if "Recipe" in str(schema_type):
            return data

        # Check @graph for Recipe
        if "@graph" in data:
            for item in data["@graph"]:
                result = _find_recipe_in_jsonld(item)
                if result:
                    return result

    elif isinstance(data, list):
        for item in data:
            result = _find_recipe_in_jsonld(item)
            if result:
                return result

    return None


def _extract_from_jsonld(
    data: dict[str, Any], metrics: RecipeEngagementMetrics
) -> None:
    """Extract engagement metrics from JSON-LD Recipe data.

    Looks for aggregateRating schema which contains:
    - ratingValue: the star rating
    - ratingCount: number of ratings
    - reviewCount: number of reviews

    Args:
        data: Recipe JSON-LD dictionary.
        metrics: Metrics object to populate (modified in place).
    """
    rating_data = data.get("aggregateRating")
    if not rating_data or not isinstance(rating_data, dict):
        return

    # Extract rating value (0-5 scale)
    if metrics.rating is None:
        rating_val = rating_data.get("ratingValue")
        metrics.rating = _parse_float(rating_val, max_val=5.0)

    # Extract rating count
    if metrics.rating_count is None:
        count_val = rating_data.get("ratingCount")
        metrics.rating_count = _parse_int(count_val)

    # Extract review count
    if metrics.reviews is None:
        review_val = rating_data.get("reviewCount")
        metrics.reviews = _parse_int(review_val)


# =============================================================================
# Microdata Extraction
# =============================================================================


def _extract_from_microdata(
    soup: BeautifulSoup, metrics: RecipeEngagementMetrics
) -> None:
    """Extract metrics from microdata (itemprop attributes).

    Args:
        soup: Parsed HTML.
        metrics: Metrics object to populate (modified in place).
    """
    # Rating value
    if metrics.rating is None:
        elem = soup.find(attrs={"itemprop": "ratingValue"})
        if elem and isinstance(elem, Tag):
            metrics.rating = _parse_float(_get_element_value(elem), max_val=5.0)

    # Rating count
    if metrics.rating_count is None:
        elem = soup.find(attrs={"itemprop": "ratingCount"})
        if elem and isinstance(elem, Tag):
            metrics.rating_count = _parse_int(_get_element_value(elem))

    # Review count
    if metrics.reviews is None:
        elem = soup.find(attrs={"itemprop": "reviewCount"})
        if elem and isinstance(elem, Tag):
            metrics.reviews = _parse_int(_get_element_value(elem))


def _get_element_value(elem: Tag) -> str | None:
    """Get value from an HTML element.

    Checks content attribute first (for meta tags), then text content.

    Args:
        elem: BeautifulSoup element.

    Returns:
        Value string or None.
    """
    # Check content attribute (used by meta tags)
    content = elem.get("content")
    if content:
        return str(content)

    # Check value attribute
    value = elem.get("value")
    if value:
        return str(value)

    # Fall back to text content
    text = elem.get_text(strip=True)
    return text if text else None


# =============================================================================
# HTML Pattern Extraction
# =============================================================================


def _extract_from_html_patterns(
    soup: BeautifulSoup, metrics: RecipeEngagementMetrics
) -> None:
    """Extract metrics from common HTML patterns.

    Uses class/id name heuristics to find metric values.

    Args:
        soup: Parsed HTML.
        metrics: Metrics object to populate (modified in place).
    """
    # Rating
    if metrics.rating is None:
        metrics.rating = _find_rating_in_html(soup)

    # Rating count
    if metrics.rating_count is None:
        metrics.rating_count = _find_count_in_html(
            soup,
            ["rating-count", "ratings-count", "ratingcount", "num-ratings", "ratings"],
        )

    # Reviews
    if metrics.reviews is None:
        metrics.reviews = _find_count_in_html(
            soup,
            ["review-count", "reviews-count", "reviewcount", "num-reviews", "reviews"],
        )

    # Favorites/saves
    if metrics.favorites is None:
        metrics.favorites = _find_count_in_html(
            soup,
            [
                "favorites",
                "saves",
                "bookmarks",
                "likes",
                "favorite-count",
                "save-count",
            ],
        )


def _find_rating_in_html(soup: BeautifulSoup) -> float | None:
    """Find star rating in HTML using common patterns.

    Args:
        soup: Parsed HTML.

    Returns:
        Rating value (0-5) or None.
    """
    # Look for elements with rating-related class names
    patterns = [
        re.compile(r"rating", re.IGNORECASE),
        re.compile(r"stars?", re.IGNORECASE),
        re.compile(r"score", re.IGNORECASE),
    ]

    for pattern in patterns:
        # Check class attributes
        elems = soup.find_all(class_=pattern)
        for elem in elems:
            # Skip if it's likely a count (has "count" in class)
            class_attr = elem.get("class")
            if isinstance(class_attr, list):
                classes = " ".join(str(c) for c in class_attr)
            else:
                classes = str(class_attr) if class_attr else ""
            if "count" in classes.lower():
                continue

            # Try to extract a rating value
            value = _extract_rating_value(elem)
            if value is not None:
                return value

    return None


def _extract_rating_value(elem: Tag) -> float | None:
    """Extract rating value from an element.

    Looks for patterns like "4.5", "4.5/5", "4.5 out of 5", etc.

    Args:
        elem: HTML element.

    Returns:
        Rating value (0-5) or None.
    """
    # Check aria-label (common for star ratings)
    aria_label = elem.get("aria-label")
    if aria_label:
        rating = _parse_rating_from_text(str(aria_label))
        if rating is not None:
            return rating

    # Check title attribute
    title = elem.get("title")
    if title:
        rating = _parse_rating_from_text(str(title))
        if rating is not None:
            return rating

    # Check data attributes
    for attr, value in elem.attrs.items():
        if "rating" in attr.lower() or "value" in attr.lower():
            rating = _parse_float(value, max_val=5.0)
            if rating is not None:
                return rating

    # Check text content
    text = elem.get_text(strip=True)
    if text:
        rating = _parse_rating_from_text(text)
        if rating is not None:
            return rating

    return None


def _parse_rating_from_text(text: str) -> float | None:
    """Parse rating value from text.

    Handles patterns like:
    - "4.5"
    - "4.5/5"
    - "4.5 out of 5"
    - "4.5 stars"
    - "Rating: 4.5"

    Args:
        text: Text to parse.

    Returns:
        Rating value (0-5) or None.
    """
    # Pattern for "X/5" or "X out of 5"
    pattern = r"(\d+(?:\.\d+)?)\s*(?:/|out\s+of)\s*5"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return _parse_float(match.group(1), max_val=5.0)

    # Pattern for standalone decimal (likely a rating)
    pattern = r"(\d+\.\d+)"
    match = re.search(pattern, text)
    if match:
        value = float(match.group(1))
        if 0 <= value <= 5:
            return value

    return None


def _find_count_in_html(soup: BeautifulSoup, keywords: list[str]) -> int | None:
    """Find a count value in HTML using class/id patterns.

    Args:
        soup: Parsed HTML.
        keywords: List of keywords to search for in class/id names.

    Returns:
        Count value or None.
    """
    for keyword in keywords:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)

        # Search by class
        elems = soup.find_all(class_=pattern)
        for elem in elems:
            count = _extract_count_from_element(elem)
            if count is not None:
                return count

        # Search by id
        elems = soup.find_all(id=pattern)
        for elem in elems:
            count = _extract_count_from_element(elem)
            if count is not None:
                return count

    return None


def _extract_count_from_element(elem: Tag) -> int | None:
    """Extract count value from an element.

    Args:
        elem: HTML element.

    Returns:
        Count value or None.
    """
    # Check data attributes
    for attr, value in elem.attrs.items():
        if "count" in attr.lower() or "total" in attr.lower():
            count = _parse_int(value)
            if count is not None:
                return count

    # Check text content
    text = elem.get_text(strip=True)
    return _extract_count_from_text(text)


def _extract_count_from_text(text: str) -> int | None:
    """Extract count from text like "1,234 reviews" or "(567)".

    Args:
        text: Text to parse.

    Returns:
        Count value or None.
    """
    if not text:
        return None

    # Remove commas from numbers
    text = text.replace(",", "")

    # Try to find a number
    match = re.search(r"(\d+)", text)
    if match:
        return int(match.group(1))

    return None


# =============================================================================
# Link Extraction Helpers
# =============================================================================


def _is_recipe_link(link: Tag) -> bool:
    """Check if a link appears to be a recipe link.

    Args:
        link: Anchor element.

    Returns:
        True if likely a recipe link.
    """
    href_attr = link.get("href", "")
    href = str(href_attr) if href_attr else ""
    if not href:
        return False

    # Skip non-recipe URL patterns
    skip_url_patterns = [
        r"/category/",
        r"/categories/",
        r"/tag/",
        r"/tags/",
        r"/author/",
        r"/search",
        r"/login",
        r"/logout",
        r"/signup",
        r"/sign-up",
        r"/register",
        r"/about",
        r"/contact",
        r"/account/",
        r"/profile/",
        r"/favorites",
        r"/saved",
        r"/collections",
        r"/authentication/",
        r"/support",
        r"/help",
        r"/faq",
        r"/privacy",
        r"/terms",
        r"/newsletter",
        r"/subscribe",
        r"/add-recipe",
        r"/submit-recipe",
        r"/all-recipes",
        r"/recipes-by-",
        r"/dinner/$",
        r"/lunch/$",
        r"/breakfast/$",
        r"/dessert/$",
        r"/appetizer/$",
        r"/dinners/?$",
        r"/lunches/?$",
        r"/breakfasts/?$",
        r"/desserts/?$",
        r"/appetizers/?$",
        r"/meals/?$",
        r"/cuisines/?$",
        r"/ingredients/?$",
        r"/cooking-tips",
        r"/how-to",
        r"/gallery",
        r"/photos",
        r"/videos?/?$",
        r"/magazine",
        r"/shop",
        r"/store",
        r"/products",
        r"/news/?$",
        r"/trending/?$",
        r"/editors-picks",
        r"#",
        r"javascript:",
        r"mailto:",
    ]
    for pattern in skip_url_patterns:
        if re.search(pattern, href, re.IGNORECASE):
            return False

    # Get and validate link text
    text = link.get_text(strip=True)
    text_lower = text.lower()

    # Skip empty or very short text (navigation items are usually short)
    if len(text) < 5:
        return False

    # Skip single-word links (real recipes have multi-word names)
    word_count = len(text.split())
    if word_count < 2:
        return False

    # Skip navigation-like link text
    skip_text_patterns = [
        r"^log\s*(in|out)",
        r"^sign\s*(in|up|out)",
        r"^help",
        r"^about",
        r"^contact",
        r"^subscribe",
        r"^newsletter",
        r"^add\s+a?\s*recipe",
        r"^submit\s+a?\s*recipe",
        r"^saved?\s+recipes?",
        r"^my\s+(recipes?|account|profile)",
        r"^all\s+recipes?",
        r"^more\s+recipes?",
        r"^view\s+(all|more)",
        r"^see\s+(all|more)",
        r"^recipes?\s+by\s+",
        r"^(dinner|lunch|breakfast|dessert|appetizer)s?$",
        r"^recipes?$",
        r"^(quick|easy|healthy|best)\s+(meals?|recipes?)$",
        r"^get\s+the\s+magazine",
        r"^(join|become)\s+(now|a\s+member)",
        r"^(start|begin)\s+(cooking|now)",
        r"^find\s+recipes?",
        r"^browse\s+(all|recipes?)",
        r"^explore\s+",
        r"^shop\s+",
        r"^watch\s+",
        r"^read\s+more$",
        r"^learn\s+more$",
        r"^(next|previous|back|home)$",
    ]
    for pattern in skip_text_patterns:
        if re.search(pattern, text_lower):
            return False

    # Must have a reasonably specific recipe-like URL pattern
    # Individual recipe pages typically have an ID or descriptive slug
    recipe_url_patterns = [
        r"/recipe/\d+/",  # /recipe/12345/ (AllRecipes style with ID)
        r"/recipe/[a-z]+-[a-z]+-[a-z]+",  # /recipe/garlic-butter-chicken (3+ word slug)
        r"/recipes/[a-z]+-[a-z]+-[a-z]+",  # /recipes/garlic-butter-chicken
        r"/\d{4,}/[a-z]",  # /12345/recipe-name (4+ digit ID + name)
        r"-\d{5,}($|/|\?)",  # slug-1234567 (long ID suffix, like Serious Eats)
        r"-recipe-\d+",  # something-recipe-12345
        # Additional patterns for broader coverage:
        r"/recipes/\d+/[a-z]",  # NYT: /recipes/1234567/carbonara
        r"/recipe/[a-z]+-[a-z]+",  # 2-word recipes: /recipe/beef-stew
        r"^/[a-z]+-[a-z]+-[a-z]+/$",  # Simple 3-word slugs: /chocolate-chip-cookies/
    ]
    for pattern in recipe_url_patterns:
        if re.search(pattern, href, re.IGNORECASE):
            return True

    return False


def _resolve_url(href: str, base_url: str) -> str | None:
    """Resolve a potentially relative URL to absolute.

    Args:
        href: URL or path from link.
        base_url: Base URL for resolution.

    Returns:
        Absolute URL or None if invalid.
    """
    if not href:
        return None

    # Already absolute
    if href.startswith(("http://", "https://")):
        return href

    # Protocol-relative
    if href.startswith("//"):
        return f"https:{href}"

    # Relative URL
    base_url = base_url.rstrip("/")
    if href.startswith("/"):
        # Parse base URL to get origin
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{href}"

    return f"{base_url}/{href}"


def _extract_recipe_name(link: Tag, container: Tag) -> str | None:
    """Extract recipe name from link and its container.

    Args:
        link: Anchor element.
        container: Parent container element.

    Returns:
        Recipe name or None.
    """
    # Try link text first
    name = _extract_link_text(link)
    if name and len(name) > 3:
        return name

    # Try heading in container
    heading = container.find(["h1", "h2", "h3", "h4", "h5", "h6"])
    if heading:
        text = heading.get_text(strip=True)
        if text:
            # Clean rating/review suffixes
            text = re.sub(r"[\d,]+\s*Ratings?$", "", text, flags=re.IGNORECASE)
            text = re.sub(r"[\d,]+\s*Reviews?$", "", text, flags=re.IGNORECASE)
            text = text.strip()
            if text:
                return str(text)

    # Try card title class
    title_elem = container.find(class_=re.compile(r"title|name|heading", re.IGNORECASE))
    if title_elem:
        text = title_elem.get_text(strip=True)
        if text:
            # Clean rating/review suffixes
            text = re.sub(r"[\d,]+\s*Ratings?$", "", text, flags=re.IGNORECASE)
            text = re.sub(r"[\d,]+\s*Reviews?$", "", text, flags=re.IGNORECASE)
            text = text.strip()
            if text:
                return str(text)

    return None


def _extract_link_text(link: Tag) -> str | None:
    """Extract meaningful text from a link.

    Args:
        link: Anchor element.

    Returns:
        Link text or None.
    """
    text: str | None = None

    # Try direct text
    raw_text = link.get_text(strip=True)
    if raw_text:
        text = str(raw_text)

    # Try title attribute
    if not text:
        title = link.get("title")
        if title:
            text = str(title)

    # Try aria-label
    if not text:
        aria_label = link.get("aria-label")
        if aria_label:
            text = str(aria_label)

    # Try img alt text
    if not text:
        img = link.find("img")
        if img and isinstance(img, Tag):
            alt = img.get("alt")
            if alt:
                text = str(alt)

    # Clean rating/review suffixes if we found text
    if text:
        text = re.sub(r"[\d,]+\s*Ratings?$", "", text, flags=re.IGNORECASE)
        text = re.sub(r"[\d,]+\s*Reviews?$", "", text, flags=re.IGNORECASE)
        text = text.strip()

    return text if text else None


# =============================================================================
# Value Parsing Helpers
# =============================================================================


def _parse_float(value: Any, max_val: float | None = None) -> float | None:
    """Parse a value to float with optional max bound.

    Args:
        value: Value to parse.
        max_val: Maximum allowed value (for validation).

    Returns:
        Float value or None if invalid.
    """
    if value is None:
        return None

    try:
        if isinstance(value, str):
            # Remove commas and common suffixes
            value = value.replace(",", "").strip()
            # Extract first number
            match = re.search(r"(\d+(?:\.\d+)?)", value)
            if match:
                value = match.group(1)

        result = float(value)

        if max_val is not None and result > max_val:
            return None
    except (ValueError, TypeError):
        return None
    else:
        return result if result >= 0 else None


def _parse_int(value: Any) -> int | None:
    """Parse a value to int.

    Args:
        value: Value to parse.

    Returns:
        Int value or None if invalid.
    """
    if value is None:
        return None

    try:
        if isinstance(value, str):
            # Remove commas and extract first number
            value = value.replace(",", "").strip()
            match = re.search(r"(\d+)", value)
            if match:
                value = match.group(1)

        result = int(float(value))
    except (ValueError, TypeError):
        return None
    else:
        return result if result >= 0 else None
