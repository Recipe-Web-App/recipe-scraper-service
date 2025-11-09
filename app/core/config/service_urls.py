"""Service URL configuration.

Centralized configuration for downstream service URLs. URLs are hardcoded for the
development environment. Update these URLs directly when deploying to production.
"""


class ServiceURLs:
    """Centralized service URLs configuration.

    Provides access to downstream service endpoints via static methods. URLs are private
    class attributes accessed through static methods.
    """

    _AUTH_SERVICE_TOKEN_URL = (
        "http://auth-service:8080/api/v1/auth/oauth2/token"  # nosec B105
    )
    _NOTIFICATION_SERVICE_URL = "http://notification-service:8000"
    _USER_MANAGEMENT_SERVICE_URL = "http://user-management-service:8000"

    @staticmethod
    def auth_service_token_url() -> str:
        """Get OAuth2 token endpoint for service-to-service authentication.

        Returns:
            OAuth2 token endpoint URL
        """
        return ServiceURLs._AUTH_SERVICE_TOKEN_URL

    @staticmethod
    def notification_service_url() -> str:
        """Get base URL for notification service.

        Returns:
            Notification service base URL
        """
        return ServiceURLs._NOTIFICATION_SERVICE_URL

    @staticmethod
    def user_management_service_url() -> str:
        """Get base URL for user management service.

        Returns:
            User management service base URL
        """
        return ServiceURLs._USER_MANAGEMENT_SERVICE_URL
