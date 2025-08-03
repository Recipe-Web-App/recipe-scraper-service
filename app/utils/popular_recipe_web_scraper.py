"""Utility to scrape popular recipes from a given URL."""

import json
import re

import httpx
from bs4 import BeautifulSoup, Tag

from app.api.v1.schemas.common.web_recipe import WebRecipe
from app.core.config.config import settings
from app.core.logging import get_logger
from app.exceptions.custom_exceptions import RecipeScrapingError

_log = get_logger(__name__)


def scrape_popular_recipes(url: str, max_recipes: int = 10) -> list[WebRecipe]:
    """Scrape popular recipes from the given URL.

    Args:     url (str): The URL to scrape for popular recipes from.     max_recipes
    (int): Maximum number of recipes to return.

    Returns:     list[WebRecipe]: A list of WebRecipe objects containing the scraped
    recipes.

    Raises:     RecipeScrapingError: If the URL cannot be scraped or parsed.
    """
    _log.info("Scraping popular recipes from: {}", url)
    _log.trace("Configuration: max_recipes={}", max_recipes)
    scraped_recipes: list[WebRecipe] = []

    try:
        # Make HTTP request with proper headers to avoid blocking
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

        _log.trace("Making HTTP request to {} with timeout=30.0s", url)
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

        _log.trace(
            "HTTP response received: status={}, content_length={}",
            response.status_code,
            len(response.content),
        )

        # Parse HTML content
        _log.trace("Parsing HTML content with BeautifulSoup")
        soup = BeautifulSoup(response.content, "html.parser")
        _log.trace(
            "HTML parsed successfully, document title: {}",
            soup.title.string if soup.title else "No title",
        )

        # Try different strategies to find recipe links based on common patterns
        _log.trace("Starting recipe link extraction using multiple strategies")
        recipe_links = _extract_recipe_links(soup, url, max_recipes)
        _log.trace(
            "Recipe link extraction completed, found {} links",
            len(recipe_links),
        )

        for i, (recipe_url, recipe_name) in enumerate(recipe_links):
            _log.trace(
                "Processing recipe {}/{}: name='{}', url='{}'",
                i + 1,
                len(recipe_links),
                recipe_name,
                recipe_url,
            )
            scraped_recipes.append(
                WebRecipe(
                    recipe_name=recipe_name,
                    url=recipe_url,
                ),
            )

        _log.info("Successfully scraped {} recipes from {}", len(scraped_recipes), url)

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code} error"
        _log.error("Failed to fetch {}: {}", url, error_msg)
        raise RecipeScrapingError(url, error_msg) from e

    except httpx.RequestError as e:
        error_msg = f"Network error: {e!s}"
        _log.error("Network error fetching {}: {}", url, error_msg)
        raise RecipeScrapingError(url, error_msg) from e

    except Exception as e:
        _log.exception("Unexpected error scraping {}", url, e)
        error_msg = f"Unexpected error: {e!r}"
        raise RecipeScrapingError(url, error_msg) from e

    return scraped_recipes


def _extract_recipe_links(
    soup: BeautifulSoup,
    base_url: str,
    max_recipes: int,
) -> list[tuple[str, str]]:
    """Extract recipe links and names from parsed HTML.

    This function tries multiple strategies to find recipe links based on common
    patterns used by recipe websites.

    Args:     soup: BeautifulSoup object of the parsed HTML.     base_url: The base URL
    for resolving relative links.     max_recipes: Maximum number of recipes to extract.

    Returns:     list[tuple[str, str]]: List of (recipe_url, recipe_name) tuples.
    """
    _log.trace("Starting _extract_recipe_links with max_recipes={}", max_recipes)
    recipe_links: list[tuple[str, str]] = []

    # Strategy 1: Look for links containing "recipe" in the URL
    _log.trace("Strategy 1: Extracting recipe URL links")
    url_links = _extract_recipe_url_links(soup, base_url, max_recipes)
    _log.trace("Strategy 1 found {} recipe URL links", len(url_links))
    recipe_links.extend(url_links)

    # Strategy 2: Look for structured data or recipe-specific selectors
    if len(recipe_links) < max_recipes:
        remaining = max_recipes - len(recipe_links)
        _log.trace(
            "Strategy 2: Extracting structured recipe links (need {} more)",
            remaining,
        )
        structured_links = _extract_structured_recipe_links(soup, base_url, remaining)
        _log.trace("Strategy 2 found {} structured recipe links", len(structured_links))
        recipe_links.extend(structured_links)

    # Strategy 3: Look for common recipe card/item classes if we still need more
    if len(recipe_links) < max_recipes:
        remaining = max_recipes - len(recipe_links)
        _log.trace(
            "Strategy 3: Extracting recipe card links (need {} more)",
            remaining,
        )
        card_links = _extract_recipe_card_links(soup, base_url, remaining)
        _log.trace("Strategy 3 found {} recipe card links", len(card_links))
        recipe_links.extend(card_links)

    _log.trace("Extracted {} total recipe links", len(recipe_links))
    final_links = recipe_links[:max_recipes]
    _log.trace("Returning {} recipe links (limited by max_recipes)", len(final_links))
    return final_links


def _extract_recipe_url_links(
    soup: BeautifulSoup,
    base_url: str,
    max_recipes: int,
) -> list[tuple[str, str]]:
    """Extract recipe links by looking for URLs containing recipe keywords."""
    _log.trace("Starting _extract_recipe_url_links with max_recipes={}", max_recipes)
    recipe_links: list[tuple[str, str]] = []
    recipe_link_elements = soup.find_all("a", href=True)
    _log.trace("Found {} total anchor elements with href", len(recipe_link_elements))

    processed = 0
    skipped_no_recipe = 0
    skipped_no_url = 0
    skipped_invalid_name = 0
    skipped_duplicate = 0

    for link in recipe_link_elements:
        processed += 1
        if len(recipe_links) >= max_recipes:
            _log.trace("Reached max_recipes limit, stopping URL link extraction")
            break

        href = link.get("href", "")
        if not _is_recipe_url(href):
            skipped_no_recipe += 1
            continue

        full_url = _resolve_url(href, base_url)
        if not full_url:
            skipped_no_url += 1
            _log.trace("Failed to resolve URL for href: {}", href)
            continue

        recipe_name = _extract_recipe_name(link)
        if not recipe_name or not _is_valid_recipe_name(recipe_name):
            skipped_invalid_name += 1
            _log.trace(
                "Skipped link with invalid recipe name: '{}' (href: {})",
                recipe_name,
                href,
            )
            continue

        if full_url in [r[0] for r in recipe_links]:
            skipped_duplicate += 1
            _log.trace("Skipped duplicate URL: {}", full_url)
            continue

        _log.trace(
            "Found valid recipe URL link: name='{}', url='{}'",
            recipe_name,
            full_url,
        )
        recipe_links.append((full_url, recipe_name))

    _log.trace(
        "URL link extraction complete: processed={}, found={}, "
        "skipped_no_recipe={}, skipped_no_url={}, "
        "skipped_invalid_name={}, skipped_duplicate={}",
        processed,
        len(recipe_links),
        skipped_no_recipe,
        skipped_no_url,
        skipped_invalid_name,
        skipped_duplicate,
    )

    return recipe_links


def _extract_recipe_card_links(
    soup: BeautifulSoup,
    base_url: str,
    max_recipes: int,
) -> list[tuple[str, str]]:
    """Extract recipe links by looking for common recipe card/item classes."""
    _log.trace("Starting _extract_recipe_card_links with max_recipes={}", max_recipes)
    recipe_links: list[tuple[str, str]] = []
    recipe_cards = soup.find_all(
        class_=lambda x: x
        and any(
            keyword in x.lower()
            for keyword in ["recipe", "card", "item", "post", "article"]
        ),
    )
    _log.trace("Found {} recipe card elements", len(recipe_cards))

    processed = 0
    skipped_no_link = 0
    skipped_no_url = 0
    skipped_invalid_name = 0
    skipped_duplicate = 0

    for card in recipe_cards:
        processed += 1
        if len(recipe_links) >= max_recipes:
            _log.trace("Reached max_recipes limit, stopping card link extraction")
            break

        link = card.find("a", href=True)
        if not link:
            skipped_no_link += 1
            continue

        href = link.get("href", "")
        full_url = _resolve_url(href, base_url)
        if not full_url:
            skipped_no_url += 1
            _log.trace("Failed to resolve URL for card href: {}", href)
            continue

        recipe_name = (
            _extract_recipe_name(link)
            or card.get_text(strip=True)[:100]
            or "Unknown Recipe"
        )

        if not _is_valid_recipe_name(recipe_name):
            skipped_invalid_name += 1
            _log.trace(
                "Skipped card with invalid recipe name: '{}' (href: {})",
                recipe_name,
                href,
            )
            continue

        if full_url in [r[0] for r in recipe_links]:
            skipped_duplicate += 1
            _log.trace("Skipped duplicate card URL: {}", full_url)
            continue

        _log.trace(
            "Found valid recipe card link: name='{}', url='{}'",
            recipe_name,
            full_url,
        )
        recipe_links.append((full_url, recipe_name))

    _log.trace(
        "Card link extraction complete: processed={}, found={}, "
        "skipped_no_link={}, skipped_no_url={}, "
        "skipped_invalid_name={}, skipped_duplicate={}",
        processed,
        len(recipe_links),
        skipped_no_link,
        skipped_no_url,
        skipped_invalid_name,
        skipped_duplicate,
    )

    return recipe_links


def _extract_structured_recipe_links(
    soup: BeautifulSoup,
    base_url: str,
    max_recipes: int,
) -> list[tuple[str, str]]:
    """Extract recipe links using structured data and recipe-specific selectors."""
    _log.trace(
        "Starting _extract_structured_recipe_links with max_recipes={}",
        max_recipes,
    )
    recipe_links: list[tuple[str, str]] = []

    # Look for JSON-LD structured data for recipes
    _log.trace("Extracting JSON-LD structured data recipes")
    json_ld_links = _extract_json_ld_recipes(soup, base_url, max_recipes)
    _log.trace("JSON-LD extraction found {} recipes", len(json_ld_links))
    recipe_links.extend(json_ld_links)

    # Look for recipe-specific microdata if we need more
    if len(recipe_links) < max_recipes:
        remaining = max_recipes - len(recipe_links)
        _log.trace("Extracting microdata recipes (need {} more)", remaining)
        microdata_links = _extract_microdata_recipes(soup, base_url, remaining)
        _log.trace("Microdata extraction found {} recipes", len(microdata_links))
        recipe_links.extend(microdata_links)

    _log.trace(
        "Structured recipe link extraction complete: found {} total recipes",
        len(recipe_links),
    )
    return recipe_links


def _extract_json_ld_recipes(
    soup: BeautifulSoup,
    base_url: str,
    max_recipes: int,
) -> list[tuple[str, str]]:
    """Extract recipe links from JSON-LD structured data."""
    _log.trace("Starting _extract_json_ld_recipes with max_recipes={}", max_recipes)
    recipe_links: list[tuple[str, str]] = []

    json_lds = soup.find_all("script", type="application/ld+json")
    _log.trace("Found {} JSON-LD script elements", len(json_lds))

    processed = 0
    skipped_parse_error = 0
    skipped_not_recipe = 0
    skipped_missing_data = 0
    skipped_invalid_name = 0
    skipped_duplicate = 0

    for json_ld in json_lds:
        processed += 1
        if len(recipe_links) >= max_recipes:
            _log.trace("Reached max_recipes limit, stopping JSON-LD extraction")
            break

        try:
            data = json.loads(json_ld.string)
            _log.trace("Successfully parsed JSON-LD data, type: {}", type(data))

            if not isinstance(data, dict) or data.get("@type") != "Recipe":
                skipped_not_recipe += 1
                _log.trace(
                    "Skipped JSON-LD: not a recipe (type: {})",
                    data.get("@type") if isinstance(data, dict) else "non-dict",
                )
                continue

            recipe_url = data.get("url") or data.get("mainEntityOfPage", {}).get("@id")
            recipe_name = data.get("name")

            if not recipe_url or not recipe_name:
                skipped_missing_data += 1
                _log.trace(
                    "Skipped JSON-LD recipe missing data: url={}, name={}",
                    bool(recipe_url),
                    bool(recipe_name),
                )
                continue

            if not _is_valid_recipe_name(recipe_name):
                skipped_invalid_name += 1
                _log.trace(
                    "Skipped JSON-LD recipe with invalid name: '{}'",
                    recipe_name,
                )
                continue

            full_url = _resolve_url(recipe_url, base_url)
            if not full_url:
                _log.trace("Failed to resolve JSON-LD recipe URL: {}", recipe_url)
                continue

            if full_url in [r[0] for r in recipe_links]:
                skipped_duplicate += 1
                _log.trace("Skipped duplicate JSON-LD recipe URL: {}", full_url)
                continue

            _log.trace(
                "Found valid JSON-LD recipe: name='{}', url='{}'",
                recipe_name,
                full_url,
            )
            recipe_links.append((full_url, recipe_name))

        except (json.JSONDecodeError, AttributeError, TypeError) as e:
            skipped_parse_error += 1
            _log.trace("Failed to parse JSON-LD data: {}", str(e))
            continue

    _log.trace(
        "JSON-LD extraction complete: processed={}, found={}, "
        "skipped_parse_error={}, skipped_not_recipe={}, "
        "skipped_missing_data={}, skipped_invalid_name={}, skipped_duplicate={}",
        processed,
        len(recipe_links),
        skipped_parse_error,
        skipped_not_recipe,
        skipped_missing_data,
        skipped_invalid_name,
        skipped_duplicate,
    )

    return recipe_links


def _extract_microdata_recipes(
    soup: BeautifulSoup,
    base_url: str,
    max_recipes: int,
) -> list[tuple[str, str]]:
    """Extract recipe links from microdata."""
    _log.trace("Starting _extract_microdata_recipes with max_recipes={}", max_recipes)
    recipe_links: list[tuple[str, str]] = []

    recipe_items = soup.find_all(
        attrs={"itemtype": lambda x: x and "recipe" in x.lower()},
    )
    _log.trace("Found {} microdata recipe items", len(recipe_items))

    processed = 0
    skipped_no_link = 0
    skipped_no_url = 0
    skipped_invalid_name = 0
    skipped_duplicate = 0

    for item in recipe_items:
        processed += 1
        if len(recipe_links) >= max_recipes:
            _log.trace("Reached max_recipes limit, stopping microdata extraction")
            break

        link = item.find("a", href=True)
        if not link:
            skipped_no_link += 1
            continue

        href = link.get("href", "")
        full_url = _resolve_url(href, base_url)
        if not full_url:
            skipped_no_url += 1
            _log.trace("Failed to resolve microdata recipe URL: {}", href)
            continue

        # Look for recipe name in structured data
        name_elem = item.find(attrs={"itemprop": "name"})
        recipe_name = (
            name_elem.get_text(strip=True) if name_elem else _extract_recipe_name(link)
        )

        if not _is_valid_recipe_name(recipe_name):
            skipped_invalid_name += 1
            _log.trace(
                "Skipped microdata recipe with invalid name: '{}' (href: {})",
                recipe_name,
                href,
            )
            continue

        if full_url in [r[0] for r in recipe_links]:
            skipped_duplicate += 1
            _log.trace("Skipped duplicate microdata recipe URL: {}", full_url)
            continue

        _log.trace(
            "Found valid microdata recipe: name='{}', url='{}'",
            recipe_name,
            full_url,
        )
        recipe_links.append((full_url, recipe_name))

    _log.trace(
        "Microdata extraction complete: processed={}, found={}, "
        "skipped_no_link={}, skipped_no_url={}, "
        "skipped_invalid_name={}, skipped_duplicate={}",
        processed,
        len(recipe_links),
        skipped_no_link,
        skipped_no_url,
        skipped_invalid_name,
        skipped_duplicate,
    )

    return recipe_links


MIN_RECIPE_NAME_LENGTH = 3
MIN_VALID_RECIPE_NAME_LENGTH = 5
MAX_RECIPE_NAME_LENGTH = 100


def _is_recipe_url(href: str) -> bool:
    """Check if a URL appears to be a recipe URL."""
    if not href:
        return False

    href_lower = href.lower()

    # Must contain recipe-related keywords
    recipe_keywords = ["recipe", "recipes"]
    has_recipe_keyword = any(keyword in href_lower for keyword in recipe_keywords)

    # Exclude navigation, admin, and category pages from config
    exclude_keywords = settings.web_scraper_url_exclude_keywords
    has_exclude_keyword = any(keyword in href_lower for keyword in exclude_keywords)

    # URL should contain "recipe" but not be a category/navigation page
    is_valid = has_recipe_keyword and not has_exclude_keyword

    _log.trace(
        "URL validation: href='{}', has_recipe={}, has_exclude={}, is_valid={}",
        href,
        has_recipe_keyword,
        has_exclude_keyword,
        is_valid,
    )

    return is_valid


def _is_valid_recipe_name(name: str) -> bool:
    """Check if a recipe name looks like an actual recipe."""
    if not name or name == "Unknown Recipe":
        _log.trace("Recipe name validation failed: empty or 'Unknown Recipe'")
        return False

    name_lower = name.lower().strip()

    # Names that are too short or generic
    if len(name_lower) < MIN_RECIPE_NAME_LENGTH:
        _log.trace(
            "Recipe name validation failed: too short ({}): '{}'",
            len(name_lower),
            name,
        )
        return False

    # Exclude navigation and UI elements from config
    exclude_names = settings.web_scraper_exclude_names

    # Check if the name is in our exclude list
    if name_lower in exclude_names:
        _log.trace(
            "Recipe name validation failed: in exclude list: '{}'",
            name,
        )
        return False

    # Check if it starts with common navigation words from config
    nav_prefixes = settings.web_scraper_nav_prefixes
    if any(name_lower.startswith(prefix) for prefix in nav_prefixes):
        _log.trace(
            "Recipe name validation failed: starts with nav prefix: '{}'",
            name,
        )
        return False

    # Check if it matches category patterns (these are likely category pages)
    if _is_category_name(name_lower):
        _log.trace(
            "Recipe name validation failed: matches category pattern: '{}'",
            name,
        )
        return False

    # Look for specific recipe indicators (food words) from config
    food_indicators = settings.web_scraper_food_indicators

    # If it contains specific food words, it's likely a recipe
    has_food_word = any(indicator in name_lower for indicator in food_indicators)

    # Must have food indicators and be reasonable length
    is_valid = (
        has_food_word
        and MIN_VALID_RECIPE_NAME_LENGTH <= len(name_lower) <= MAX_RECIPE_NAME_LENGTH
    )

    _log.trace(
        "Recipe name validation: name='{}', length={}, has_food_word={}, is_valid={}",
        name,
        len(name_lower),
        has_food_word,
        is_valid,
    )

    return is_valid


def _is_category_name(name_lower: str) -> bool:
    """Check if a name matches patterns typical of category pages."""
    # Check against patterns
    for pattern in settings.web_scraper_category_patterns:
        if re.match(pattern, name_lower, re.IGNORECASE):
            _log.trace("Category pattern match: '{}' matches '{}'", name_lower, pattern)
            return True

    # Check single words and simple phrases
    words = name_lower.split()
    if len(words) == 1 and words[0] in settings.web_scraper_single_word_categories:
        _log.trace("Single word category match: '{}'", name_lower)
        return True

    # Check for compound category names (ingredient + category)
    min_compound_words = 2
    if len(words) >= min_compound_words:
        # Check patterns like "maple syrup", "quick bread"
        last_word = words[-1]
        if last_word in settings.web_scraper_single_word_categories:
            _log.trace("Compound category match: '{}'", name_lower)
            return True

        # Check for phrases with category indicators
        if any(word in settings.web_scraper_category_indicators for word in words):
            _log.trace("Category indicator match: '{}'", name_lower)
            return True

    return False


def _resolve_url(href: str, base_url: str) -> str | None:
    """Resolve relative URLs to absolute URLs."""
    if not href:
        _log.trace("URL resolution failed: empty href")
        return None

    if href.startswith("/"):
        resolved = base_url.rstrip("/") + href
        _log.trace("Resolved relative URL: '{}' -> '{}'", href, resolved)
        return resolved
    if href.startswith("http"):
        _log.trace("URL already absolute: '{}'", href)
        return href

    _log.trace("URL resolution failed: unsupported format: '{}'", href)
    return None


def _extract_recipe_name(link: Tag) -> str:
    """Extract recipe name from a link element."""
    text = link.get_text(strip=True)
    title = link.get("title", "")
    alt = link.get("alt", "")

    # Ensure we have strings, not lists
    if isinstance(title, list):
        title = " ".join(title) if title else ""
    if isinstance(alt, list):
        alt = " ".join(alt) if alt else ""

    recipe_name = text or title or alt or "Unknown Recipe"

    # Clean up the recipe name by removing common suffixes
    cleaned_name = _clean_recipe_name(recipe_name)
    truncated_name = cleaned_name.strip()[:100]

    _log.trace(
        "Extracted recipe name: text='{}', title='{}', alt='{}', "
        "cleaned='{}', final='{}'",
        text,
        title,
        alt,
        cleaned_name,
        truncated_name,
    )

    return truncated_name


def _clean_recipe_name(name: str) -> str:
    """Clean up recipe name by removing timing and ratings metadata."""
    if not name:
        return name

    cleaned = name.strip()

    # Simple patterns to remove timing and ratings (most common issues)
    simple_patterns = [
        r"\d+\s*mins?\s*ratings?$",  # "30 minsRatings", "22 mins"
        r"\d+\s*ratings?$",  # "51Ratings", "12Ratings"
        r"ratings?$",  # "Ratings"
    ]

    for pattern in simple_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip()

    # Remove extra whitespace
    return re.sub(r"\s+", " ", cleaned)
