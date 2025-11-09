"""Base service class for downstream services using OAuth2 authentication.

Provides common functionality for services that need to authenticate with downstream
APIs using OAuth2 client credentials flow.
"""

import httpx

from app.core.logging import get_logger
from app.utils.service_token_manager import ServiceTokenManager


class BaseServiceWithOAuth2:
    """Base class for downstream services requiring OAuth2 authentication.

    Provides automatic token injection via httpx event hooks and manages the HTTP
    client lifecycle. Services requiring OAuth2 authentication should inherit from
    this class.

    Example:
        class UserManagementService(BaseServiceWithOAuth2):
            def __init__(self, token_manager: ServiceTokenManager):
                super().__init__(
                    token_manager=token_manager,
                    base_url=ServiceURLs.user_management_service_url(),
                    scope="user:read",
                )

            async def get_users(self) -> list[User]:
                client = await self._get_client()
                response = await client.get("/api/v1/users")
                return [User(**u) for u in response.json()]
    """

    def __init__(
        self,
        token_manager: ServiceTokenManager,
        base_url: str,
        scope: str,
    ) -> None:
        """Initialize the base service with OAuth2 authentication.

        Args:
            token_manager: ServiceTokenManager instance for token acquisition
            base_url: Base URL for the downstream service
            scope: OAuth2 scope for token requests (e.g., "user:read")
        """
        self.token_manager = token_manager
        self.base_url = base_url
        self.scope = scope
        self._client: httpx.AsyncClient | None = None
        self._log = get_logger(self.__class__.__name__)

    async def _add_auth_token(self, request: httpx.Request) -> None:
        """Event hook to inject OAuth2 Bearer token into request headers.

        This method is called automatically by httpx before each request.

        Args:
            request: The outgoing HTTP request to modify
        """
        token = await self.token_manager.get_service_token(scope=self.scope)
        request.headers["Authorization"] = f"Bearer {token}"
        self._log.debug(
            "Added OAuth2 token to request",
            extra={"url": str(request.url), "scope": self.scope},
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client with auth event hook.

        Lazily initializes the HTTP client on first use. The client is configured
        with the base URL, timeout, and automatic token injection.

        Returns:
            Configured async HTTP client instance
        """
        if self._client is None:
            self._log.debug(
                "Initializing HTTP client",
                extra={"base_url": self.base_url, "scope": self.scope},
            )
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=10.0,
                event_hooks={"request": [self._add_auth_token]},
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client and cleanup resources.

        This should be called when the service is no longer needed, typically during
        application shutdown via FastAPI lifespan events.
        """
        if self._client is not None:
            self._log.debug("Closing HTTP client")
            await self._client.aclose()
            self._client = None
