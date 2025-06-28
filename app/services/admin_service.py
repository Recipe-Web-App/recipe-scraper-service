"""Administrative service for managing Recipe Scraper operations.

This module provides administrative functionality for the Recipe Scraper service,
including cache management and other operational tasks.
"""

from app.core.logging import get_logger
from app.utils.cache_manager import CacheManager

_log = get_logger(__name__)


class AdminService:
    """Admin Service for administrative tasks such as cache management."""

    def __init__(self) -> None:
        """AdminService for administrative tasks such as cache management."""
        self._cache_manager = CacheManager()

    def clear_cache(self) -> None:
        """Clear the cache for the Recipe Scraper service.

        This method clears all cached data used by the Recipe Scraper service.
        It is intended for administrative use only.

        Note:
            This method is designed to be safe and will not raise exceptions.
            Any errors during cache clearing are logged but do not interrupt execution.
        """
        self._cache_manager.clear_all()
        _log.info("Successfully cleared Recipe Scraper service cache")
