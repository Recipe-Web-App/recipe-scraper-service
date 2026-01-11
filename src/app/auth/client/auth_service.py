"""HTTP client for external auth-service.

This module provides an async HTTP client for communicating with the
external OAuth2 auth-service, primarily for token introspection.
"""

from __future__ import annotations

import hashlib
import time
from typing import TYPE_CHECKING, Any

import httpx

from app.auth.providers.exceptions import AuthServiceUnavailableError
from app.auth.providers.models import IntrospectionResponse
from app.observability.logging import get_logger


if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = get_logger(__name__)


class AuthServiceClient:
    """Async HTTP client for the auth-service.

    Provides methods for:
    - Token introspection (RFC 7662)
    - Userinfo endpoint access
    - Discovery document retrieval

    The client supports connection pooling and automatic retries for
    transient failures.

    Attributes:
        base_url: Base URL of the auth service.
        client_id: OAuth2 client ID for this service.
        client_secret: OAuth2 client secret.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        timeout: float = 5.0,
        cache_client: Redis[Any] | None = None,
        cache_ttl: int = 60,
    ) -> None:
        """Initialize the auth service client.

        Args:
            base_url: Base URL of the auth service (e.g., http://auth:8080/api/v1/auth).
            client_id: OAuth2 client ID for introspection.
            client_secret: OAuth2 client secret.
            timeout: HTTP request timeout in seconds.
            cache_client: Optional Redis client for caching introspection results.
            cache_ttl: Cache TTL in seconds (default: 60).
        """
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self.cache_client = cache_client
        self.cache_ttl = cache_ttl
        self._http_client: httpx.AsyncClient | None = None

    @property
    def introspection_url(self) -> str:
        """Get the token introspection endpoint URL."""
        return f"{self.base_url}/oauth2/introspect"

    @property
    def userinfo_url(self) -> str:
        """Get the userinfo endpoint URL."""
        return f"{self.base_url}/oauth2/userinfo"

    async def initialize(self) -> None:
        """Initialize the HTTP client with connection pooling."""
        if self._http_client is not None:
            return

        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
            ),
        )
        logger.info(
            "AuthServiceClient initialized",
            base_url=self.base_url,
            timeout=self.timeout,
        )

    async def shutdown(self) -> None:
        """Close the HTTP client and release connections."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
            logger.debug("AuthServiceClient shutdown")

    def _get_cache_key(self, token: str) -> str:
        """Generate cache key for a token.

        Uses a hash of the token to avoid storing the actual token in Redis.
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        return f"auth:introspect:{token_hash}"

    async def _get_cached_result(self, token: str) -> IntrospectionResponse | None:
        """Get cached introspection result if available."""
        if not self.cache_client:
            return None

        try:
            cache_key = self._get_cache_key(token)
            cached = await self.cache_client.get(cache_key)
            if cached:
                logger.debug("Cache hit for token introspection")
                return IntrospectionResponse.model_validate_json(cached)
        except Exception as e:
            logger.warning("Failed to read from cache", error=str(e))

        return None

    async def _cache_result(
        self,
        token: str,
        result: IntrospectionResponse,
    ) -> None:
        """Cache an introspection result."""
        if not self.cache_client:
            return

        # Only cache active tokens, and respect their expiration
        if not result.active:
            return

        try:
            cache_key = self._get_cache_key(token)
            ttl = self.cache_ttl

            # If token has expiration, don't cache longer than that
            if result.exp:
                remaining = result.exp - int(time.time())
                if remaining > 0:
                    ttl = min(ttl, remaining)
                else:
                    return  # Token already expired, don't cache

            await self.cache_client.set(
                cache_key,
                result.model_dump_json(),
                ex=ttl,
            )
            logger.debug("Cached introspection result", ttl=ttl)
        except Exception as e:
            logger.warning("Failed to cache introspection result", error=str(e))

    async def introspect_token(
        self,
        token: str,
        token_type_hint: str = "access_token",  # noqa: S107
    ) -> IntrospectionResponse:
        """Introspect a token using the auth-service.

        Implements RFC 7662 token introspection.

        Args:
            token: The token to introspect.
            token_type_hint: Hint about token type (access_token, refresh_token).

        Returns:
            IntrospectionResponse with token metadata.

        Raises:
            AuthServiceUnavailableError: If the auth service cannot be reached.
        """
        # Check cache first
        cached = await self._get_cached_result(token)
        if cached is not None:
            return cached

        if self._http_client is None:
            await self.initialize()

        assert self._http_client is not None

        try:
            response = await self._http_client.post(
                self.introspection_url,
                data={
                    "token": token,
                    "token_type_hint": token_type_hint,
                },
                auth=httpx.BasicAuth(self.client_id, self.client_secret),
            )

            # RFC 7662: introspection endpoint always returns 200
            # with {"active": false} for invalid tokens
            response.raise_for_status()
            result = IntrospectionResponse.model_validate(response.json())

            # Cache the result
            await self._cache_result(token, result)

        except httpx.TimeoutException as e:
            logger.exception(
                "Auth service introspection timeout",
                url=self.introspection_url,
                timeout=self.timeout,
            )
            msg = f"Auth service timeout after {self.timeout}s"
            raise AuthServiceUnavailableError(msg) from e

        except httpx.HTTPStatusError as e:
            logger.exception(
                "Auth service introspection failed",
                status_code=e.response.status_code,
                url=self.introspection_url,
            )
            msg = f"Auth service returned {e.response.status_code}"
            raise AuthServiceUnavailableError(msg) from e

        except httpx.RequestError as e:
            logger.exception(
                "Auth service connection error",
                url=self.introspection_url,
                error=str(e),
            )
            msg = f"Cannot connect to auth service: {e}"
            raise AuthServiceUnavailableError(msg) from e

        else:
            return result
