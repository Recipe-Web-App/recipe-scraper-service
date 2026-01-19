"""Recipe scraping exceptions.

This module defines exceptions specific to recipe scraping operations.
These exceptions are caught by the endpoint layer and converted to
appropriate HTTP responses.
"""

from __future__ import annotations


class ScrapingError(Exception):
    """Base exception for scraping errors."""


class UnsupportedURLError(ScrapingError):
    """Raised when the URL is not from a supported recipe site.

    The recipe-scrapers library doesn't support this domain,
    and JSON-LD fallback also failed.
    """


class ScrapingFetchError(ScrapingError):
    """Raised when fetching the URL fails.

    This includes connection errors, timeouts, and HTTP errors
    when retrieving the recipe page.
    """


class ScrapingTimeoutError(ScrapingFetchError):
    """Raised when fetching the URL times out."""


class ScrapingParseError(ScrapingError):
    """Raised when parsing the recipe data fails.

    The page was fetched successfully, but the recipe data
    could not be extracted from the HTML.
    """


class RecipeNotFoundError(ScrapingError):
    """Raised when no recipe data is found on the page.

    The URL was valid and the page was fetched, but no
    structured recipe data could be located.
    """
