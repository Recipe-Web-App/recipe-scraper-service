"""Service token manager dependency injection.

Provides singleton access to the ServiceTokenManager instance.
"""

from app.utils.service_token_manager import ServiceTokenManager

_service_token_manager: ServiceTokenManager | None = None


def get_service_token_manager() -> ServiceTokenManager:
    """Get singleton instance of ServiceTokenManager.

    Returns:
        Singleton ServiceTokenManager instance
    """
    global _service_token_manager
    if _service_token_manager is None:
        _service_token_manager = ServiceTokenManager()
    return _service_token_manager
