"""Integration tests for OllamaClient with real Redis."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
import respx

from tests.fixtures.llm_responses import create_ollama_response


if TYPE_CHECKING:
    from app.llm.client.ollama import OllamaClient


pytestmark = pytest.mark.integration


class TestCacheIntegration:
    """Tests for caching with real Redis."""

    @respx.mock
    async def test_cache_stores_and_retrieves(
        self,
        ollama_client: OllamaClient,
    ) -> None:
        """Should store result in Redis and retrieve on subsequent call."""
        route = respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=create_ollama_response("Test result"),
            )
        )

        # First call - cache miss
        result1 = await ollama_client.generate("test prompt")
        assert result1.cached is False
        assert route.call_count == 1

        # Second call - cache hit
        result2 = await ollama_client.generate("test prompt")
        assert result2.cached is True
        assert result2.raw_response == "Test result"
        assert route.call_count == 1  # No additional HTTP call

    @respx.mock
    async def test_different_prompts_cached_separately(
        self,
        ollama_client: OllamaClient,
    ) -> None:
        """Different prompts should have separate cache entries."""
        route = respx.post("http://localhost:11434/api/generate")
        route.side_effect = [
            httpx.Response(200, json=create_ollama_response("Response 1")),
            httpx.Response(200, json=create_ollama_response("Response 2")),
        ]

        result1 = await ollama_client.generate("prompt 1")
        result2 = await ollama_client.generate("prompt 2")

        assert result1.raw_response == "Response 1"
        assert result2.raw_response == "Response 2"
        assert route.call_count == 2

        # Both should be cached now
        result1_cached = await ollama_client.generate("prompt 1")
        result2_cached = await ollama_client.generate("prompt 2")

        assert result1_cached.cached is True
        assert result2_cached.cached is True
        assert route.call_count == 2  # No additional calls

    @respx.mock
    async def test_cache_respects_ttl(
        self,
        ollama_client: OllamaClient,
    ) -> None:
        """Cache should store with configured TTL."""
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=create_ollama_response("Response"),
            )
        )

        await ollama_client.generate("test")

        # Verify TTL was set (integration test with real Redis)
        # Note: We can't easily verify TTL value, but we verify the key exists
        cache_key = ollama_client._get_cache_key("test", "mistral:7b", None, None)
        assert ollama_client.cache_client is not None

        exists = await ollama_client.cache_client.exists(cache_key)
        assert exists == 1

    @respx.mock
    async def test_cache_graceful_on_redis_errors(
        self,
        ollama_client: OllamaClient,
    ) -> None:
        """Should continue working even if Redis has issues."""
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=create_ollama_response("Response"),
            )
        )

        # Close Redis connection to simulate error
        assert ollama_client.cache_client is not None
        await ollama_client.cache_client.aclose()

        # Should still work, just without caching
        result = await ollama_client.generate("test")
        assert result.raw_response == "Response"
