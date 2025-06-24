"""Manager for accessing instances of downstream services.

This module provides a centralized way to manage and access downstream service
instances, ensuring proper resource management and avoiding duplicate HTTP client
instances.
"""

from functools import lru_cache
from typing import Any, TypeVar, cast

from app.core.logging import get_logger
from app.services.downstream.spoonacular_service import SpoonacularService

_log = get_logger(__name__)

# Type variable for service types
T = TypeVar("T")


class _DownstreamServiceManager:
    """Manager for downstream service instances.

    Provides access to downstream services to ensure proper
    resource management and avoid creating multiple HTTP client instances.

    Note: This is a private class. Use get_downstream_service_manager() instead.
    """

    def __init__(self) -> None:
        """Initialize the service manager."""
        self._services: dict[type[Any], Any] = {}
        _log.debug("Initialized DownstreamServiceManager")

    def get_service(self, service_class: type[T]) -> T:
        """Get or create a service instance.

        Args:
            service_class: The service class to get an instance of

        Returns:
            Service instance of the requested type
        """
        if service_class not in self._services:
            _log.debug("Creating new instance of {}", service_class.__name__)
            self._services[service_class] = service_class()

        return cast("T", self._services[service_class])

    def get_spoonacular_service(self) -> SpoonacularService:
        """Get the Spoonacular service instance.

        Returns:
            SpoonacularService instance
        """
        return self.get_service(SpoonacularService)

    def close_all(self) -> None:
        """Close all service instances and clean up resources."""
        _log.debug("Closing all downstream services")

        for service_class, service_instance in self._services.items():
            try:
                # Try to call cleanup methods if they exist
                if hasattr(service_instance, "close"):
                    service_instance.close()
                elif hasattr(service_instance, "__del__"):
                    service_instance.__del__()
                _log.debug("Closed service instance: {}", service_class.__name__)
            except (AttributeError, RuntimeError) as e:
                _log.warning(
                    "Error closing service {}: {}",
                    service_class.__name__,
                    e,
                )

        self._services.clear()

    def __del__(self) -> None:
        """Cleanup when manager is destroyed."""
        self.close_all()


@lru_cache(maxsize=1)
def get_downstream_service_manager() -> _DownstreamServiceManager:
    """Get the downstream service manager instance.

    Uses @lru_cache to ensure only one instance is created and reused.

    Returns:
        _DownstreamServiceManager: The service manager instance
    """
    return _DownstreamServiceManager()
