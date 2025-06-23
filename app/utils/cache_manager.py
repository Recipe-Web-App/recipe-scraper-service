"""Cache manager for storing and retrieving cached data with expiration.

This module provides a file-based caching system that can be used across the application
for caching any JSON-serializable data with configurable expiration times.
"""

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TypeVar

from app.core.logging import get_logger

_log = get_logger(__name__)

T = TypeVar("T")


class CacheManager:
    """Manages file-based caching with expiration times.

    This class provides a simple file-based cache that stores data as JSON files
    with associated metadata for expiration tracking. It's designed to be reusable
    across different parts of the application.

    Example:
        cache = CacheManager()
        cache.set("my_data", {"key": "value"}, expiry_hours=24)
        data = cache.get("my_data")  # Returns data if not expired
    """

    def __init__(self, cache_dir: str | None = None) -> None:
        """Initialize cache manager with cache directory.

        Args:
            cache_dir: Directory to store cache files. If None, uses default.
        """
        if cache_dir is None:
            # Use a secure temporary directory with proper permissions
            default_cache_dir = Path(tempfile.gettempdir()) / "recipe_cache"
            self.cache_dir = default_cache_dir
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        _log.debug("Initialized CacheManager with cache directory: {}", self.cache_dir)

    def _get_cache_file_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key.

        Args:
            cache_key: The cache key

        Returns:
            Path to the cache data file
        """
        return self.cache_dir / f"{cache_key}.json"

    def _get_metadata_file_path(self, cache_key: str) -> Path:
        """Get the metadata file path for a cache key.

        Args:
            cache_key: The cache key

        Returns:
            Path to the cache metadata file
        """
        return self.cache_dir / f"{cache_key}_metadata.json"

    def set(
        self,
        cache_key: str,
        data: list[dict[str, Any]] | dict[str, Any],
        expiry_hours: int = 24,
    ) -> None:
        """Store data in cache with expiration time.

        Args:
            cache_key: Unique key for the cached data
            data: Data to cache (must be JSON serializable)
            expiry_hours: Hours until cache expires (default: 24)

        Raises:
            OSError: If data cannot be written to cache files
            ValueError: If data cannot be JSON serialized
        """
        try:
            cache_file = self._get_cache_file_path(cache_key)
            metadata_file = self._get_metadata_file_path(cache_key)

            # Store the data
            with cache_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)

            # Store metadata with expiration time
            now = datetime.now(tz=UTC)
            expiry_time = now + timedelta(hours=expiry_hours)
            metadata = {
                "cached_at": now.isoformat(),
                "expires_at": expiry_time.isoformat(),
                "expiry_hours": expiry_hours,
                "cache_key": cache_key,
            }

            with metadata_file.open("w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

            _log.info(
                "Cached data for key '{}' with expiry at {}",
                cache_key,
                expiry_time,
            )

        except (OSError, ValueError) as e:
            _log.error("Failed to cache data for key '{}': {}", cache_key, e)
            raise

    def get(self, cache_key: str) -> list[dict[str, Any]] | dict[str, Any] | None:
        """Retrieve data from cache if not expired.

        Args:
            cache_key: Unique key for the cached data

        Returns:
            Cached data if valid and not expired, None otherwise
        """
        try:
            cache_file = self._get_cache_file_path(cache_key)
            metadata_file = self._get_metadata_file_path(cache_key)

            # Check if files exist
            if not cache_file.exists() or not metadata_file.exists():
                _log.debug("Cache miss for key '{}' - files don't exist", cache_key)
                return None

            # Load and check metadata
            with metadata_file.open(encoding="utf-8") as f:
                metadata = json.load(f)

            expires_at = datetime.fromisoformat(metadata["expires_at"])

            if datetime.now(tz=UTC) > expires_at:
                _log.info("Cache expired for key '{}' at {}", cache_key, expires_at)
                self.delete(cache_key)
                return None

            # Load and return data
            with cache_file.open(encoding="utf-8") as f:
                data: list[dict[str, Any]] | dict[str, Any] = json.load(f)

        except (OSError, ValueError, KeyError) as e:
            _log.error("Failed to retrieve cache for key '{}': {}", cache_key, e)
            return None
        else:
            _log.debug("Cache hit for key '{}'", cache_key)
            return data

    def delete(self, cache_key: str) -> None:
        """Delete cached data and metadata files.

        Args:
            cache_key: Unique key for the cached data
        """
        try:
            cache_file = self._get_cache_file_path(cache_key)
            metadata_file = self._get_metadata_file_path(cache_key)

            if cache_file.exists():
                cache_file.unlink()
                _log.debug("Deleted cache file for key '{}'", cache_key)
            if metadata_file.exists():
                metadata_file.unlink()
                _log.debug("Deleted metadata file for key '{}'", cache_key)

        except OSError as e:
            _log.error("Failed to delete cache for key '{}': {}", cache_key, e)

    def is_valid(self, cache_key: str) -> bool:
        """Check if cache exists and is not expired.

        Args:
            cache_key: Unique key for the cached data

        Returns:
            True if cache is valid and not expired, False otherwise
        """
        return self.get(cache_key) is not None

    def clear_all(self) -> None:
        """Clear all cached data and metadata files."""
        try:
            files_deleted = 0
            for file in self.cache_dir.glob("*.json"):
                file.unlink()
                files_deleted += 1
            _log.info("Cleared {} cache files", files_deleted)
        except OSError as e:
            _log.error("Failed to clear cache: {}", e)
