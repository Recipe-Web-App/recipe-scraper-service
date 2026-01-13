"""Unit tests for OllamaClient.

Tests cover:
- HTTP request construction
- Response parsing
- Error handling
- Caching behavior
- Retry logic
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx
from pydantic import BaseModel

from app.llm.client.ollama import OllamaClient
from app.llm.exceptions import (
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    LLMUnavailableError,
    LLMValidationError,
)
from tests.fixtures.llm_responses import create_ollama_response


pytestmark = pytest.mark.unit


class SampleSchema(BaseModel):
    """Sample schema for testing structured output."""

    title: str
    items: list[str]


class TestOllamaClientInitialization:
    """Tests for client initialization and lifecycle."""

    async def test_initialize_creates_http_client(self) -> None:
        """Should create HTTP client on initialize."""
        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
        )

        await client.initialize()

        assert client._http_client is not None
        await client.shutdown()

    async def test_shutdown_closes_http_client(self) -> None:
        """Should close HTTP client on shutdown."""
        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
        )

        await client.initialize()
        await client.shutdown()

        assert client._http_client is None

    async def test_initialize_idempotent(self) -> None:
        """Should be safe to call initialize multiple times."""
        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
        )

        await client.initialize()
        first_client = client._http_client
        await client.initialize()

        assert client._http_client is first_client
        await client.shutdown()

    def test_generate_url_strips_trailing_slash(self) -> None:
        """Should strip trailing slash from base URL."""
        client = OllamaClient(
            base_url="http://localhost:11434/",
            model="mistral:7b",
        )

        assert client.generate_url == "http://localhost:11434/api/generate"


class TestOllamaClientGenerate:
    """Tests for generate method."""

    @respx.mock
    async def test_generate_success(self) -> None:
        """Should return completion result on success."""
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=create_ollama_response("Hello, world!"),
            )
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            cache_enabled=False,
        )

        result = await client.generate("Say hello")

        assert result.raw_response == "Hello, world!"
        assert result.model == "mistral:7b"
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 5
        assert result.cached is False

        await client.shutdown()

    @respx.mock
    async def test_generate_with_structured_output(self) -> None:
        """Should parse structured JSON output when schema provided."""
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=create_ollama_response('{"title": "Test", "items": ["a", "b"]}'),
            )
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            cache_enabled=False,
        )

        result = await client.generate("Extract data", schema=SampleSchema)

        assert result.parsed is not None
        assert result.parsed.title == "Test"
        assert result.parsed.items == ["a", "b"]

        await client.shutdown()

    @respx.mock
    async def test_generate_structured_validation_error(self) -> None:
        """Should raise LLMValidationError when response doesn't match schema."""
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=create_ollama_response('{"invalid": "data"}'),
            )
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            cache_enabled=False,
        )

        with pytest.raises(LLMValidationError):
            await client.generate("Extract data", schema=SampleSchema)

        await client.shutdown()

    @respx.mock
    async def test_generate_with_system_prompt(self) -> None:
        """Should include system prompt in request."""
        route = respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=create_ollama_response("Response"),
            )
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            cache_enabled=False,
        )

        await client.generate("Test", system="You are a helpful assistant.")

        assert route.called
        request_body = json.loads(route.calls.last.request.content)
        assert request_body["system"] == "You are a helpful assistant."

        await client.shutdown()

    @respx.mock
    async def test_generate_with_custom_model(self) -> None:
        """Should use specified model instead of default."""
        route = respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=create_ollama_response("Response", model="llama3:8b"),
            )
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            cache_enabled=False,
        )

        result = await client.generate("Test", model="llama3:8b")

        request_body = json.loads(route.calls.last.request.content)
        assert request_body["model"] == "llama3:8b"
        assert result.model == "llama3:8b"

        await client.shutdown()


class TestOllamaClientGenerateStructured:
    """Tests for generate_structured method."""

    @respx.mock
    async def test_returns_parsed_model_directly(self) -> None:
        """Should return the parsed Pydantic model directly."""
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=create_ollama_response('{"title": "Test", "items": ["x"]}'),
            )
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            cache_enabled=False,
        )

        result = await client.generate_structured("Extract", schema=SampleSchema)

        assert isinstance(result, SampleSchema)
        assert result.title == "Test"
        assert result.items == ["x"]

        await client.shutdown()


class TestOllamaClientErrorHandling:
    """Tests for error handling."""

    @respx.mock
    async def test_timeout_error(self) -> None:
        """Should raise LLMTimeoutError on timeout."""
        respx.post("http://localhost:11434/api/generate").mock(
            side_effect=httpx.TimeoutException("timeout")
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            max_retries=0,
            cache_enabled=False,
        )

        with pytest.raises(LLMTimeoutError):
            await client.generate("test")

        await client.shutdown()

    @respx.mock
    async def test_connection_error(self) -> None:
        """Should raise LLMUnavailableError on connection failure."""
        respx.post("http://localhost:11434/api/generate").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            max_retries=0,
            cache_enabled=False,
        )

        with pytest.raises(LLMUnavailableError):
            await client.generate("test")

        await client.shutdown()

    @respx.mock
    async def test_http_error_response(self) -> None:
        """Should raise LLMResponseError on HTTP error."""
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(500, json={"error": "Internal error"})
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            max_retries=0,
            cache_enabled=False,
        )

        with pytest.raises(LLMResponseError):
            await client.generate("test")

        await client.shutdown()

    @respx.mock
    async def test_rate_limit_error(self) -> None:
        """Should raise LLMRateLimitError on 429."""
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(429, json={"error": "Too many requests"})
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            max_retries=0,
            cache_enabled=False,
        )

        with pytest.raises(LLMRateLimitError):
            await client.generate("test")

        await client.shutdown()


class TestOllamaClientRetry:
    """Tests for retry logic."""

    @respx.mock
    async def test_retry_on_timeout(self) -> None:
        """Should retry on timeout up to max_retries."""
        route = respx.post("http://localhost:11434/api/generate")
        route.side_effect = [
            httpx.TimeoutException("timeout"),
            httpx.TimeoutException("timeout"),
            httpx.Response(200, json=create_ollama_response("Success after retry")),
        ]

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            max_retries=2,
            cache_enabled=False,
        )

        result = await client.generate("test")

        assert result.raw_response == "Success after retry"
        assert route.call_count == 3

        await client.shutdown()

    @respx.mock
    async def test_retry_on_connection_error(self) -> None:
        """Should retry on connection error."""
        route = respx.post("http://localhost:11434/api/generate")
        route.side_effect = [
            httpx.ConnectError("refused"),
            httpx.Response(200, json=create_ollama_response("Success")),
        ]

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            max_retries=1,
            cache_enabled=False,
        )

        result = await client.generate("test")

        assert result.raw_response == "Success"
        assert route.call_count == 2

        await client.shutdown()

    @respx.mock
    async def test_retry_exhaustion(self) -> None:
        """Should raise after max_retries exhausted."""
        respx.post("http://localhost:11434/api/generate").mock(
            side_effect=httpx.TimeoutException("timeout")
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            max_retries=2,
            cache_enabled=False,
        )

        with pytest.raises(LLMTimeoutError):
            await client.generate("test")

        await client.shutdown()

    @respx.mock
    async def test_no_retry_on_http_error(self) -> None:
        """Should not retry on HTTP errors (non-transient)."""
        route = respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(400, json={"error": "Bad request"})
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            max_retries=2,
            cache_enabled=False,
        )

        with pytest.raises(LLMResponseError):
            await client.generate("test")

        assert route.call_count == 1  # No retries

        await client.shutdown()


class TestOllamaClientCaching:
    """Tests for caching behavior."""

    @respx.mock
    async def test_cache_hit_returns_cached_result(self) -> None:
        """Should return cached result without HTTP call on cache hit."""
        mock_redis = MagicMock()
        cached_result = {
            "raw_response": "Cached response",
            "parsed": None,
            "model": "mistral:7b",
            "prompt_tokens": 5,
            "completion_tokens": 3,
            "cached": False,
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_result))

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            cache_client=mock_redis,
            cache_enabled=True,
        )

        result = await client.generate("test prompt")

        assert result.raw_response == "Cached response"
        assert result.cached is True
        mock_redis.get.assert_called_once()

        await client.shutdown()

    @respx.mock
    async def test_cache_miss_makes_request(self) -> None:
        """Should make HTTP request on cache miss."""
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()

        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=create_ollama_response("Fresh response"),
            )
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            cache_client=mock_redis,
            cache_enabled=True,
            cache_ttl=3600,
        )

        result = await client.generate("test prompt")

        assert result.raw_response == "Fresh response"
        assert result.cached is False
        mock_redis.set.assert_called_once()

        await client.shutdown()

    @respx.mock
    async def test_skip_cache_bypasses_cache(self) -> None:
        """Should bypass cache when skip_cache=True."""
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock()
        mock_redis.set = AsyncMock()

        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=create_ollama_response("Fresh response"),
            )
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            cache_client=mock_redis,
            cache_enabled=True,
        )

        await client.generate("test prompt", skip_cache=True)

        mock_redis.get.assert_not_called()
        mock_redis.set.assert_not_called()

        await client.shutdown()

    @respx.mock
    async def test_cache_disabled_skips_caching(self) -> None:
        """Should not cache when cache_enabled=False."""
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock()
        mock_redis.set = AsyncMock()

        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json=create_ollama_response("Response"),
            )
        )

        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
            cache_client=mock_redis,
            cache_enabled=False,
        )

        await client.generate("test")

        mock_redis.get.assert_not_called()
        mock_redis.set.assert_not_called()

        await client.shutdown()


class TestCacheKeyGeneration:
    """Tests for cache key generation."""

    def test_same_inputs_produce_same_key(self) -> None:
        """Same prompt/model/schema should produce same cache key."""
        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
        )

        key1 = client._get_cache_key("prompt", "mistral:7b", SampleSchema, None)
        key2 = client._get_cache_key("prompt", "mistral:7b", SampleSchema, None)

        assert key1 == key2

    def test_different_prompts_produce_different_keys(self) -> None:
        """Different prompts should produce different cache keys."""
        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
        )

        key1 = client._get_cache_key("prompt1", "mistral:7b", None, None)
        key2 = client._get_cache_key("prompt2", "mistral:7b", None, None)

        assert key1 != key2

    def test_different_models_produce_different_keys(self) -> None:
        """Different models should produce different cache keys."""
        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
        )

        key1 = client._get_cache_key("prompt", "mistral:7b", None, None)
        key2 = client._get_cache_key("prompt", "llama3:8b", None, None)

        assert key1 != key2

    def test_different_system_prompts_produce_different_keys(self) -> None:
        """Different system prompts should produce different cache keys."""
        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
        )

        key1 = client._get_cache_key("prompt", "mistral:7b", None, "system1")
        key2 = client._get_cache_key("prompt", "mistral:7b", None, "system2")

        assert key1 != key2

    def test_cache_key_has_correct_prefix(self) -> None:
        """Cache key should have llm:generate: prefix."""
        client = OllamaClient(
            base_url="http://localhost:11434",
            model="mistral:7b",
        )

        key = client._get_cache_key("prompt", "mistral:7b", None, None)

        assert key.startswith("llm:generate:")
