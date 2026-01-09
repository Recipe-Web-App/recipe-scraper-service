"""Integration tests for rate limiting.

Tests cover:
- Rate limit enforcement with real Redis
- Rate limit headers in responses
- Rate limit exceeded responses
- Different rate limits for different endpoints
"""

from __future__ import annotations

import asyncio
import uuid
from typing import TYPE_CHECKING

import pytest
import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from app.cache.rate_limit import rate_limit_exceeded_handler


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from app.core.config import Settings


pytestmark = pytest.mark.integration


@pytest.fixture
async def clean_redis(redis_url: str) -> AsyncGenerator[aioredis.Redis]:
    """Get Redis client and clean rate limit keys after test."""
    client = await aioredis.from_url(redis_url)
    yield client
    # Clean up rate limit keys after each test
    keys = await client.keys("LIMITER:*")
    if keys:
        await client.delete(*keys)
    await client.aclose()


@pytest.fixture
def rate_limited_app(
    test_settings: Settings,
    redis_url: str,
) -> FastAPI:
    """Create a minimal FastAPI app with rate limiting."""
    parts = redis_url.replace("redis://", "").split(":")
    test_settings.REDIS_HOST = parts[0]
    test_settings.REDIS_PORT = int(parts[1])

    # Use a unique key per test to avoid counter collision
    test_id = str(uuid.uuid4())[:8]

    def unique_key_func(request: Request) -> str:
        return f"test:{test_id}"

    # Create a fresh limiter with test Redis URL
    test_limiter = Limiter(
        key_func=unique_key_func,
        default_limits=["5/minute"],
        storage_uri=f"redis://{parts[0]}:{parts[1]}",
        strategy="fixed-window",
        headers_enabled=True,
    )

    app = FastAPI()
    app.state.limiter = test_limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    @app.get("/test")
    @test_limiter.limit("3/minute")
    async def test_endpoint(request: Request) -> JSONResponse:
        return JSONResponse(content={"message": "ok"})

    @app.get("/unlimited")
    async def unlimited_endpoint() -> JSONResponse:
        return JSONResponse(content={"message": "no limit"})

    return app


@pytest.fixture
async def rate_limit_client(
    rate_limited_app: FastAPI,
    clean_redis: aioredis.Redis,
) -> AsyncGenerator[AsyncClient]:
    """Create client for rate limited app."""
    async with AsyncClient(
        transport=ASGITransport(app=rate_limited_app),
        base_url="http://test",
    ) as client:
        yield client


class TestRateLimitEnforcement:
    """Tests for rate limit enforcement."""

    @pytest.mark.asyncio
    async def test_requests_within_limit_succeed(
        self,
        rate_limit_client: AsyncClient,
    ) -> None:
        """Should allow requests within the rate limit."""
        # Make 3 requests (limit is 3/minute)
        for i in range(3):
            response = await rate_limit_client.get("/test")
            assert response.status_code == 200, (
                f"Request {i + 1} failed: {response.text}"
            )

    @pytest.mark.asyncio
    async def test_requests_exceeding_limit_blocked(
        self,
        rate_limit_client: AsyncClient,
    ) -> None:
        """Should block requests exceeding the rate limit."""
        # Make requests until we hit the limit
        for i in range(4):
            response = await rate_limit_client.get("/test")
            if i < 3:
                assert response.status_code == 200, (
                    f"Request {i + 1} failed unexpectedly"
                )
            else:
                # 4th request should be blocked
                assert response.status_code == 429, (
                    f"Request {i + 1} should have been blocked"
                )

    @pytest.mark.asyncio
    async def test_rate_limit_returns_429(
        self,
        rate_limit_client: AsyncClient,
    ) -> None:
        """Should return 429 status when rate limited."""
        # Exhaust the limit
        for _ in range(3):
            await rate_limit_client.get("/test")

        # Next request should be 429
        response = await rate_limit_client.get("/test")
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limit_error_response_format(
        self,
        rate_limit_client: AsyncClient,
    ) -> None:
        """Should return proper error format when rate limited."""
        # Exhaust the limit
        for _ in range(3):
            await rate_limit_client.get("/test")

        response = await rate_limit_client.get("/test")
        data = response.json()

        assert "error" in data
        assert data["error"] == "rate_limit_exceeded"
        assert "message" in data


class TestRateLimitHeaders:
    """Tests for rate limit headers."""

    @pytest.mark.asyncio
    async def test_includes_rate_limit_headers(
        self,
        rate_limit_client: AsyncClient,
    ) -> None:
        """Should include rate limit headers in response."""
        response = await rate_limit_client.get("/test")

        # SlowAPI includes these headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    @pytest.mark.asyncio
    async def test_remaining_decrements(
        self,
        rate_limit_client: AsyncClient,
    ) -> None:
        """Should decrement remaining count with each request."""
        response1 = await rate_limit_client.get("/test")
        remaining1 = int(response1.headers.get("X-RateLimit-Remaining", 0))

        response2 = await rate_limit_client.get("/test")
        remaining2 = int(response2.headers.get("X-RateLimit-Remaining", 0))

        assert remaining2 < remaining1

    @pytest.mark.asyncio
    async def test_retry_after_header_when_limited(
        self,
        rate_limit_client: AsyncClient,
    ) -> None:
        """Should include Retry-After header when rate limited."""
        # Exhaust the limit
        for _ in range(3):
            await rate_limit_client.get("/test")

        response = await rate_limit_client.get("/test")
        assert "Retry-After" in response.headers


class TestUnlimitedEndpoints:
    """Tests for endpoints without rate limits."""

    @pytest.mark.asyncio
    async def test_unlimited_endpoint_allows_many_requests(
        self,
        rate_limit_client: AsyncClient,
    ) -> None:
        """Should allow unlimited requests to non-rate-limited endpoints."""
        # Make more requests than any reasonable limit
        for _ in range(10):
            response = await rate_limit_client.get("/unlimited")
            assert response.status_code == 200


class TestRateLimitEdgeCases:
    """Edge case tests for rate limiting."""

    @pytest.fixture
    def multi_client_app(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> FastAPI:
        """Create app with IP-based rate limiting for multi-client tests."""
        parts = redis_url.replace("redis://", "").split(":")

        def ip_key_func(request: Request) -> str:
            # Use X-Test-Client header to simulate different IPs
            return request.headers.get("X-Test-Client", "default")

        test_limiter = Limiter(
            key_func=ip_key_func,
            default_limits=["5/minute"],
            storage_uri=f"redis://{parts[0]}:{parts[1]}",
            strategy="fixed-window",
            headers_enabled=True,
        )

        app = FastAPI()
        app.state.limiter = test_limiter
        app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

        @app.get("/api")
        @test_limiter.limit("2/minute")
        async def api_endpoint(request: Request) -> JSONResponse:
            return JSONResponse(content={"status": "ok"})

        return app

    @pytest.mark.asyncio
    async def test_different_clients_have_separate_limits(
        self,
        multi_client_app: FastAPI,
        clean_redis: aioredis.Redis,
    ) -> None:
        """Should track rate limits separately for different clients."""
        async with AsyncClient(
            transport=ASGITransport(app=multi_client_app),
            base_url="http://test",
        ) as client:
            # Client A makes 2 requests (hits limit)
            for _ in range(2):
                response = await client.get(
                    "/api",
                    headers={"X-Test-Client": "client-a"},
                )
                assert response.status_code == 200

            # Client A is now rate limited
            response = await client.get(
                "/api",
                headers={"X-Test-Client": "client-a"},
            )
            assert response.status_code == 429

            # Client B should still have fresh limits
            response = await client.get(
                "/api",
                headers={"X-Test-Client": "client-b"},
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_resets_after_window(
        self,
        test_settings: Settings,
        redis_url: str,
        clean_redis: aioredis.Redis,
    ) -> None:
        """Should reset rate limit after time window expires."""
        parts = redis_url.replace("redis://", "").split(":")
        test_id = str(uuid.uuid4())[:8]

        def key_func(request: Request) -> str:
            return f"reset_test:{test_id}"

        # Use 2 second window for faster test
        test_limiter = Limiter(
            key_func=key_func,
            default_limits=["5/minute"],
            storage_uri=f"redis://{parts[0]}:{parts[1]}",
            strategy="fixed-window",
            headers_enabled=True,
        )

        app = FastAPI()
        app.state.limiter = test_limiter
        app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

        @app.get("/short")
        @test_limiter.limit("2/2second")
        async def short_window(request: Request) -> JSONResponse:
            return JSONResponse(content={"ok": True})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Exhaust the limit
            for _ in range(2):
                response = await client.get("/short")
                assert response.status_code == 200

            # Should be rate limited
            response = await client.get("/short")
            assert response.status_code == 429

            # Wait for window to reset
            await asyncio.sleep(2.5)

            # Should be allowed again
            response = await client.get("/short")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_requests_at_limit_boundary(
        self,
        test_settings: Settings,
        redis_url: str,
        clean_redis: aioredis.Redis,
    ) -> None:
        """Should handle concurrent requests near rate limit boundary."""
        parts = redis_url.replace("redis://", "").split(":")
        test_id = str(uuid.uuid4())[:8]

        def key_func(request: Request) -> str:
            return f"concurrent_test:{test_id}"

        test_limiter = Limiter(
            key_func=key_func,
            default_limits=["5/minute"],
            storage_uri=f"redis://{parts[0]}:{parts[1]}",
            strategy="fixed-window",
            headers_enabled=True,
        )

        app = FastAPI()
        app.state.limiter = test_limiter
        app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

        @app.get("/concurrent")
        @test_limiter.limit("5/minute")
        async def concurrent_endpoint(request: Request) -> JSONResponse:
            return JSONResponse(content={"ok": True})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Send 10 concurrent requests with limit of 5
            tasks = [client.get("/concurrent") for _ in range(10)]
            responses = await asyncio.gather(*tasks)

            # Exactly 5 should succeed, 5 should be rate limited
            success_count = sum(1 for r in responses if r.status_code == 200)
            limited_count = sum(1 for r in responses if r.status_code == 429)

            assert success_count == 5
            assert limited_count == 5

    @pytest.mark.asyncio
    async def test_different_endpoints_different_limits(
        self,
        test_settings: Settings,
        redis_url: str,
        clean_redis: aioredis.Redis,
    ) -> None:
        """Should apply different rate limits to different endpoints."""
        parts = redis_url.replace("redis://", "").split(":")
        test_id = str(uuid.uuid4())[:8]

        def key_func(request: Request) -> str:
            return f"multi_endpoint:{test_id}"

        test_limiter = Limiter(
            key_func=key_func,
            default_limits=["100/minute"],
            storage_uri=f"redis://{parts[0]}:{parts[1]}",
            strategy="fixed-window",
            headers_enabled=True,
        )

        app = FastAPI()
        app.state.limiter = test_limiter
        app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

        @app.get("/strict")
        @test_limiter.limit("2/minute")
        async def strict_endpoint(request: Request) -> JSONResponse:
            return JSONResponse(content={"endpoint": "strict"})

        @app.get("/lenient")
        @test_limiter.limit("10/minute")
        async def lenient_endpoint(request: Request) -> JSONResponse:
            return JSONResponse(content={"endpoint": "lenient"})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Exhaust strict endpoint limit
            for _ in range(2):
                response = await client.get("/strict")
                assert response.status_code == 200

            # Strict should be limited
            response = await client.get("/strict")
            assert response.status_code == 429

            # Lenient should still work (separate limit counter per endpoint)
            for _ in range(5):
                response = await client.get("/lenient")
                assert response.status_code == 200
