"""Unit tests for AuthServiceClient.

Tests cover:
- URL property construction
- Client initialization and shutdown
- Cache key generation
- Cache retrieval and storage
- Token introspection with error handling
"""

from __future__ import annotations

import hashlib
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.auth.client.auth_service import AuthServiceClient
from app.auth.providers.exceptions import AuthServiceUnavailableError
from app.auth.providers.models import IntrospectionResponse


pytestmark = pytest.mark.unit


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_redis() -> MagicMock:
    """Create a mock Redis client."""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def auth_client() -> AuthServiceClient:
    """Create an AuthServiceClient without cache."""
    return AuthServiceClient(
        base_url="https://auth.example.com/api/v1",
        client_id="test-client-id",
        client_secret="test-client-secret",
        timeout=5.0,
    )


@pytest.fixture
def auth_client_with_cache(mock_redis: MagicMock) -> AuthServiceClient:
    """Create an AuthServiceClient with cache."""
    return AuthServiceClient(
        base_url="https://auth.example.com/api/v1",
        client_id="test-client-id",
        client_secret="test-client-secret",
        timeout=5.0,
        cache_client=mock_redis,
        cache_ttl=60,
    )


@pytest.fixture
def active_introspection_response() -> IntrospectionResponse:
    """Create an active introspection response."""
    return IntrospectionResponse(
        active=True,
        sub="user-123",
        scope="read write",
        client_id="test-client",
        token_type="Bearer",
        exp=int(time.time()) + 3600,
        iat=int(time.time()),
        iss="https://auth.example.com",
    )


@pytest.fixture
def inactive_introspection_response() -> IntrospectionResponse:
    """Create an inactive introspection response."""
    return IntrospectionResponse(active=False)


# =============================================================================
# URL Property Tests
# =============================================================================


class TestURLProperties:
    """Tests for URL construction properties."""

    def test_introspection_url_construction(self, auth_client: AuthServiceClient):
        """Should construct correct introspection URL."""
        assert (
            auth_client.introspection_url
            == "https://auth.example.com/api/v1/oauth2/introspect"
        )

    def test_userinfo_url_construction(self, auth_client: AuthServiceClient):
        """Should construct correct userinfo URL."""
        assert (
            auth_client.userinfo_url
            == "https://auth.example.com/api/v1/oauth2/userinfo"
        )

    def test_url_strips_trailing_slash(self):
        """Should strip trailing slash from base URL."""
        client = AuthServiceClient(
            base_url="https://auth.example.com/api/v1/",
            client_id="test",
            client_secret="test",
        )
        assert (
            client.introspection_url
            == "https://auth.example.com/api/v1/oauth2/introspect"
        )
        assert client.userinfo_url == "https://auth.example.com/api/v1/oauth2/userinfo"


# =============================================================================
# Initialization Tests
# =============================================================================


class TestInitialization:
    """Tests for client initialization."""

    async def test_initialize_creates_http_client(self, auth_client: AuthServiceClient):
        """Should create HTTP client on initialize."""
        assert auth_client._http_client is None

        await auth_client.initialize()

        assert auth_client._http_client is not None
        assert isinstance(auth_client._http_client, httpx.AsyncClient)

        # Cleanup
        await auth_client.shutdown()

    async def test_initialize_already_initialized_returns_early(
        self, auth_client: AuthServiceClient
    ):
        """Should return early if already initialized."""
        await auth_client.initialize()
        first_client = auth_client._http_client

        # Call initialize again
        await auth_client.initialize()

        # Should be the same client instance
        assert auth_client._http_client is first_client

        # Cleanup
        await auth_client.shutdown()

    async def test_initialize_sets_timeout_and_limits(
        self, auth_client: AuthServiceClient
    ):
        """Should configure timeout and connection limits."""
        await auth_client.initialize()

        assert auth_client._http_client is not None
        assert auth_client._http_client.timeout.connect == 5.0

        # Cleanup
        await auth_client.shutdown()


# =============================================================================
# Shutdown Tests
# =============================================================================


class TestShutdown:
    """Tests for client shutdown."""

    async def test_shutdown_closes_http_client(self, auth_client: AuthServiceClient):
        """Should close HTTP client on shutdown."""
        await auth_client.initialize()
        assert auth_client._http_client is not None

        await auth_client.shutdown()

        assert auth_client._http_client is None

    async def test_shutdown_when_not_initialized(self, auth_client: AuthServiceClient):
        """Should handle shutdown when client was never initialized."""
        assert auth_client._http_client is None

        # Should not raise
        await auth_client.shutdown()

        assert auth_client._http_client is None


# =============================================================================
# Cache Key Generation Tests
# =============================================================================


class TestCacheKeyGeneration:
    """Tests for cache key generation."""

    def test_get_cache_key_generates_hash(self, auth_client: AuthServiceClient):
        """Should generate SHA256-based cache key."""
        token = "test-token-12345"
        cache_key = auth_client._get_cache_key(token)

        expected_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        assert cache_key == f"auth:introspect:{expected_hash}"

    def test_get_cache_key_consistent(self, auth_client: AuthServiceClient):
        """Should generate consistent keys for same token."""
        token = "test-token-12345"

        key1 = auth_client._get_cache_key(token)
        key2 = auth_client._get_cache_key(token)

        assert key1 == key2

    def test_get_cache_key_different_for_different_tokens(
        self, auth_client: AuthServiceClient
    ):
        """Should generate different keys for different tokens."""
        key1 = auth_client._get_cache_key("token-1")
        key2 = auth_client._get_cache_key("token-2")

        assert key1 != key2


# =============================================================================
# Cache Retrieval Tests
# =============================================================================


class TestCacheRetrieval:
    """Tests for cache retrieval."""

    async def test_get_cached_result_returns_none_without_cache_client(
        self, auth_client: AuthServiceClient
    ):
        """Should return None when no cache client is configured."""
        result = await auth_client._get_cached_result("test-token")

        assert result is None

    async def test_get_cached_result_cache_miss(
        self,
        auth_client_with_cache: AuthServiceClient,
        mock_redis: MagicMock,
    ):
        """Should return None on cache miss."""
        mock_redis.get = AsyncMock(return_value=None)

        result = await auth_client_with_cache._get_cached_result("test-token")

        assert result is None
        mock_redis.get.assert_called_once()

    async def test_get_cached_result_cache_hit(
        self,
        auth_client_with_cache: AuthServiceClient,
        mock_redis: MagicMock,
        active_introspection_response: IntrospectionResponse,
    ):
        """Should return cached response on cache hit."""
        cached_data = active_introspection_response.model_dump_json()
        mock_redis.get = AsyncMock(return_value=cached_data)

        result = await auth_client_with_cache._get_cached_result("test-token")

        assert result is not None
        assert result.active is True
        assert result.sub == "user-123"

    async def test_get_cached_result_handles_cache_error(
        self,
        auth_client_with_cache: AuthServiceClient,
        mock_redis: MagicMock,
    ):
        """Should return None and log warning on cache error."""
        mock_redis.get = AsyncMock(side_effect=Exception("Redis connection failed"))

        result = await auth_client_with_cache._get_cached_result("test-token")

        assert result is None

    async def test_get_cached_result_handles_invalid_json(
        self,
        auth_client_with_cache: AuthServiceClient,
        mock_redis: MagicMock,
    ):
        """Should return None on invalid cached JSON."""
        mock_redis.get = AsyncMock(return_value="invalid-json")

        result = await auth_client_with_cache._get_cached_result("test-token")

        assert result is None


# =============================================================================
# Cache Storage Tests
# =============================================================================


class TestCacheStorage:
    """Tests for cache storage."""

    async def test_cache_result_skips_without_cache_client(
        self,
        auth_client: AuthServiceClient,
        active_introspection_response: IntrospectionResponse,
    ):
        """Should skip caching when no cache client is configured."""
        # Should not raise
        await auth_client._cache_result("test-token", active_introspection_response)

    async def test_cache_result_skips_inactive_tokens(
        self,
        auth_client_with_cache: AuthServiceClient,
        mock_redis: MagicMock,
        inactive_introspection_response: IntrospectionResponse,
    ):
        """Should not cache inactive tokens."""
        await auth_client_with_cache._cache_result(
            "test-token", inactive_introspection_response
        )

        mock_redis.set.assert_not_called()

    async def test_cache_result_stores_active_token(
        self,
        auth_client_with_cache: AuthServiceClient,
        mock_redis: MagicMock,
        active_introspection_response: IntrospectionResponse,
    ):
        """Should cache active tokens."""
        await auth_client_with_cache._cache_result(
            "test-token", active_introspection_response
        )

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert "auth:introspect:" in call_args[0][0]

    async def test_cache_result_respects_token_expiry(
        self,
        auth_client_with_cache: AuthServiceClient,
        mock_redis: MagicMock,
    ):
        """Should use shorter TTL if token expires before cache TTL."""
        # Token expires in 30 seconds
        response = IntrospectionResponse(
            active=True,
            sub="user-123",
            exp=int(time.time()) + 30,
        )

        await auth_client_with_cache._cache_result("test-token", response)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        # TTL should be min(cache_ttl=60, remaining=~30) = ~30
        assert call_args.kwargs["ex"] <= 30

    async def test_cache_result_skips_already_expired_token(
        self,
        auth_client_with_cache: AuthServiceClient,
        mock_redis: MagicMock,
    ):
        """Should not cache tokens that are already expired."""
        response = IntrospectionResponse(
            active=True,
            sub="user-123",
            exp=int(time.time()) - 10,  # Expired 10 seconds ago
        )

        await auth_client_with_cache._cache_result("test-token", response)

        mock_redis.set.assert_not_called()

    async def test_cache_result_handles_cache_error(
        self,
        auth_client_with_cache: AuthServiceClient,
        mock_redis: MagicMock,
        active_introspection_response: IntrospectionResponse,
    ):
        """Should log warning and continue on cache error."""
        mock_redis.set = AsyncMock(side_effect=Exception("Redis write failed"))

        # Should not raise
        await auth_client_with_cache._cache_result(
            "test-token", active_introspection_response
        )

    async def test_cache_result_uses_default_ttl_when_no_expiry(
        self,
        auth_client_with_cache: AuthServiceClient,
        mock_redis: MagicMock,
    ):
        """Should use default TTL when token has no expiration."""
        response = IntrospectionResponse(
            active=True,
            sub="user-123",
            exp=None,
        )

        await auth_client_with_cache._cache_result("test-token", response)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args.kwargs["ex"] == 60  # Default TTL


# =============================================================================
# Token Introspection Tests
# =============================================================================


class TestIntrospectToken:
    """Tests for token introspection."""

    async def test_introspect_token_success(
        self,
        auth_client: AuthServiceClient,
        active_introspection_response: IntrospectionResponse,
    ):
        """Should successfully introspect token."""
        mock_response = MagicMock()
        mock_response.json.return_value = active_introspection_response.model_dump()
        mock_response.raise_for_status = MagicMock()

        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        auth_client._http_client = mock_http_client

        result = await auth_client.introspect_token("test-token")

        assert result.active is True
        assert result.sub == "user-123"
        mock_http_client.post.assert_called_once()

    async def test_introspect_token_initializes_client_if_needed(
        self,
        auth_client: AuthServiceClient,
        active_introspection_response: IntrospectionResponse,
    ):
        """Should auto-initialize HTTP client if not initialized."""
        assert auth_client._http_client is None

        with patch.object(
            auth_client, "initialize", new_callable=AsyncMock
        ) as mock_init:
            mock_response = MagicMock()
            mock_response.json.return_value = active_introspection_response.model_dump()
            mock_response.raise_for_status = MagicMock()

            mock_http_client = MagicMock()
            mock_http_client.post = AsyncMock(return_value=mock_response)

            async def set_client():
                auth_client._http_client = mock_http_client

            mock_init.side_effect = set_client

            result = await auth_client.introspect_token("test-token")

            mock_init.assert_called_once()
            assert result.active is True

    async def test_introspect_token_uses_cache(
        self,
        auth_client_with_cache: AuthServiceClient,
        mock_redis: MagicMock,
        active_introspection_response: IntrospectionResponse,
    ):
        """Should return cached result without HTTP call."""
        cached_data = active_introspection_response.model_dump_json()
        mock_redis.get = AsyncMock(return_value=cached_data)

        result = await auth_client_with_cache.introspect_token("test-token")

        assert result.active is True
        assert result.sub == "user-123"
        # HTTP client should not be called when cache hit
        assert auth_client_with_cache._http_client is None

    async def test_introspect_token_timeout_raises(
        self, auth_client: AuthServiceClient
    ):
        """Should raise AuthServiceUnavailableError on timeout."""
        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(
            side_effect=httpx.TimeoutException("Connection timed out")
        )
        auth_client._http_client = mock_http_client

        with pytest.raises(AuthServiceUnavailableError, match="timeout"):
            await auth_client.introspect_token("test-token")

    async def test_introspect_token_http_error_raises(
        self, auth_client: AuthServiceClient
    ):
        """Should raise AuthServiceUnavailableError on HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Service unavailable",
            request=MagicMock(),
            response=mock_response,
        )

        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        auth_client._http_client = mock_http_client

        with pytest.raises(AuthServiceUnavailableError, match="503"):
            await auth_client.introspect_token("test-token")

    async def test_introspect_token_request_error_raises(
        self, auth_client: AuthServiceClient
    ):
        """Should raise AuthServiceUnavailableError on connection error."""
        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(
            side_effect=httpx.RequestError("Connection refused")
        )
        auth_client._http_client = mock_http_client

        with pytest.raises(AuthServiceUnavailableError, match="Cannot connect"):
            await auth_client.introspect_token("test-token")

    async def test_introspect_token_caches_result(
        self,
        auth_client_with_cache: AuthServiceClient,
        mock_redis: MagicMock,
        active_introspection_response: IntrospectionResponse,
    ):
        """Should cache successful introspection result."""
        mock_redis.get = AsyncMock(return_value=None)  # Cache miss

        mock_response = MagicMock()
        mock_response.json.return_value = active_introspection_response.model_dump()
        mock_response.raise_for_status = MagicMock()

        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        auth_client_with_cache._http_client = mock_http_client

        result = await auth_client_with_cache.introspect_token("test-token")

        assert result.active is True
        mock_redis.set.assert_called_once()

    async def test_introspect_token_with_token_type_hint(
        self,
        auth_client: AuthServiceClient,
        active_introspection_response: IntrospectionResponse,
    ):
        """Should pass token_type_hint to introspection endpoint."""
        mock_response = MagicMock()
        mock_response.json.return_value = active_introspection_response.model_dump()
        mock_response.raise_for_status = MagicMock()

        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        auth_client._http_client = mock_http_client

        await auth_client.introspect_token(
            "test-token", token_type_hint="refresh_token"
        )

        call_args = mock_http_client.post.call_args
        assert call_args.kwargs["data"]["token_type_hint"] == "refresh_token"

    async def test_introspect_token_uses_basic_auth(
        self,
        auth_client: AuthServiceClient,
        active_introspection_response: IntrospectionResponse,
    ):
        """Should use HTTP Basic Auth for introspection."""
        mock_response = MagicMock()
        mock_response.json.return_value = active_introspection_response.model_dump()
        mock_response.raise_for_status = MagicMock()

        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        auth_client._http_client = mock_http_client

        await auth_client.introspect_token("test-token")

        call_args = mock_http_client.post.call_args
        auth = call_args.kwargs["auth"]
        assert isinstance(auth, httpx.BasicAuth)
        assert (
            auth._auth_header
            == httpx.BasicAuth("test-client-id", "test-client-secret")._auth_header
        )
