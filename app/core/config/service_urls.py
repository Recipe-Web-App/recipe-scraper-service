"""Service URL configuration.

Centralized configuration for downstream service URLs. URLs are loaded from
config/service_urls.yaml with sensible defaults for production.
"""

from pathlib import Path

import yaml


class ServiceURLs:
    """Centralized service URLs configuration.

    Provides access to downstream service endpoints via static methods. URLs are loaded
    from config/service_urls.yaml with fallback defaults.
    """

    _config: dict[str, str] = {}
    _loaded: bool = False

    @classmethod
    def _load_config(cls) -> None:
        """Load service URLs from config file (lazy loading, once only)."""
        if cls._loaded:
            return
        config_path = (
            Path(__file__).parent.parent.parent.parent / "config" / "service_urls.yaml"
        )
        try:
            with config_path.open("r", encoding="utf-8") as f:
                cls._config = yaml.safe_load(f) or {}
        except (FileNotFoundError, yaml.YAMLError):
            cls._config = {}
        cls._loaded = True

    @staticmethod
    def auth_service_token_url() -> str:
        """Get OAuth2 token endpoint for service-to-service authentication.

        Returns:
            OAuth2 token endpoint URL
        """
        ServiceURLs._load_config()
        return ServiceURLs._config.get(
            "auth_service_token_url",
            "http://auth-service.local/api/v1/auth/oauth2/token",
        )

    @staticmethod
    def notification_service_url() -> str:
        """Get base URL for notification service.

        Returns:
            Notification service base URL
        """
        ServiceURLs._load_config()
        return ServiceURLs._config.get(
            "notification_service_url",
            "http://notification-service.local",
        )

    @staticmethod
    def user_management_service_url() -> str:
        """Get base URL for user management service.

        Returns:
            User management service base URL
        """
        ServiceURLs._load_config()
        return ServiceURLs._config.get(
            "user_management_service_url",
            "http://user-management.local",
        )
