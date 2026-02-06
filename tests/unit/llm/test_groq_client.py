"""Unit tests for GroqClient.

Tests cover:
- HTTP request construction
- Response parsing
- Error handling
- Caching behavior
- Retry logic
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx
from pydantic import BaseModel

from app.llm.client.groq import GroqClient
from app.llm.exceptions import (
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    LLMUnavailableError,
    LLMValidationError,
)
from app.llm.models import LLMCompletionResult
from tests.fixtures.llm_responses import create_groq_response


pytestmark = pytest.mark.unit

# High rate limit to disable rate limiting delays in tests
TEST_RATE_LIMIT = 10000.0


class SampleSchema(BaseModel):
    """Sample schema for testing structured output."""

    title: str
    items: list[str]


class TestGroqClientInitialization:
    """Tests for client initialization and lifecycle."""

    async def test_initialize_creates_http_client(self) -> None:
        """Should create HTTP client on initialize."""
        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
        )

        await client.initialize()

        assert client._http_client is not None
        await client.shutdown()

    async def test_shutdown_closes_http_client(self) -> None:
        """Should close HTTP client on shutdown."""
        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
        )

        await client.initialize()
        await client.shutdown()

        assert client._http_client is None

    async def test_initialize_idempotent(self) -> None:
        """Should be safe to call initialize multiple times."""
        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
        )

        await client.initialize()
        first_client = client._http_client
        await client.initialize()

        assert client._http_client is first_client
        await client.shutdown()

    def test_chat_url_default(self) -> None:
        """Should use default Groq API URL."""
        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
        )

        assert client.chat_url == "https://api.groq.com/openai/v1/chat/completions"

    def test_chat_url_custom(self) -> None:
        """Should allow custom base URL."""
        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            base_url="https://custom.groq.com/v1/",
        )

        assert client.chat_url == "https://custom.groq.com/v1/chat/completions"


class TestGroqClientGenerate:
    """Tests for generate method."""

    @respx.mock
    async def test_generate_success(self) -> None:
        """Should return completion result on success."""
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=create_groq_response("Hello, world!"),
            )
        )

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
        )

        result = await client.generate("Say hello")

        assert result.raw_response == "Hello, world!"
        assert result.model == "llama-3.1-8b-instant"
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 5
        assert result.cached is False

        await client.shutdown()

    @respx.mock
    async def test_generate_with_structured_output(self) -> None:
        """Should parse structured JSON output when schema provided."""
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=create_groq_response('{"title": "Test", "items": ["a", "b"]}'),
            )
        )

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
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
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=create_groq_response("not valid json"),
            )
        )

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
        )

        with pytest.raises(LLMValidationError):
            await client.generate("Extract data", schema=SampleSchema)

        await client.shutdown()

    @respx.mock
    async def test_generate_with_system_prompt(self) -> None:
        """Should include system message in request."""
        route = respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=create_groq_response("Response"),
            )
        )

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
        )

        await client.generate("Hello", system="Be helpful")

        assert route.called
        request_body = route.calls[0].request.content

        body = json.loads(request_body)
        assert body["messages"][0]["role"] == "system"
        assert "Be helpful" in body["messages"][0]["content"]

        await client.shutdown()


class TestGroqClientErrors:
    """Tests for error handling."""

    @respx.mock
    async def test_rate_limit_error(self) -> None:
        """Should raise LLMRateLimitError on 429."""
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(429, headers={"retry-after": "0"})
        )

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
            max_retries=0,  # Don't retry to avoid delays
        )

        with pytest.raises(LLMRateLimitError, match="rate limit"):
            await client.generate("Hello")

        await client.shutdown()

    @respx.mock
    async def test_http_error(self) -> None:
        """Should raise LLMResponseError on HTTP errors."""
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(500, json={"error": "Internal error"})
        )

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
        )

        with pytest.raises(LLMResponseError, match="500"):
            await client.generate("Hello")

        await client.shutdown()

    @respx.mock
    async def test_timeout_error(self) -> None:
        """Should raise LLMTimeoutError on timeout."""
        timeout_msg = "Timeout"
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            side_effect=httpx.TimeoutException(timeout_msg)
        )

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
            max_retries=0,
        )

        with pytest.raises(LLMTimeoutError, match="timeout"):
            await client.generate("Hello")

        await client.shutdown()

    @respx.mock
    async def test_connection_error(self) -> None:
        """Should raise LLMUnavailableError on connection errors."""
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
            max_retries=0,
        )

        with pytest.raises(LLMUnavailableError, match="Cannot connect"):
            await client.generate("Hello")

        await client.shutdown()


class TestGroqClientRetry:
    """Tests for retry behavior."""

    @respx.mock
    async def test_retry_on_timeout(self) -> None:
        """Should retry on timeout and succeed."""
        call_count = 0
        timeout_msg = "Timeout"

        def response_handler(_request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException(timeout_msg)
            return httpx.Response(200, json=create_groq_response("Success"))

        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            side_effect=response_handler
        )

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
            max_retries=2,
        )

        result = await client.generate("Hello")

        assert result.raw_response == "Success"
        assert call_count == 2

        await client.shutdown()

    @respx.mock
    async def test_no_retry_on_http_error(self) -> None:
        """Should not retry on HTTP 4xx/5xx errors."""
        call_count = 0

        def response_handler(_request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(400, json={"error": "Bad request"})

        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            side_effect=response_handler
        )

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
            max_retries=2,
        )

        with pytest.raises(LLMResponseError):
            await client.generate("Hello")

        assert call_count == 1

        await client.shutdown()


class TestGroqClientCaching:
    """Tests for caching behavior."""

    @respx.mock
    async def test_cache_hit_returns_cached_result(self) -> None:
        """Should return cached result without making HTTP request."""
        mock_redis = MagicMock()
        cached_result = {
            "raw_response": "Cached response",
            "parsed": None,
            "model": "llama-3.1-8b-instant",
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "cached": False,
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_result))

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_client=mock_redis,
            cache_enabled=True,
        )

        # No HTTP mock set up - should not be called
        result = await client.generate("Hello")

        assert result.raw_response == "Cached response"
        assert result.cached is True
        mock_redis.get.assert_called_once()

        await client.shutdown()

    @respx.mock
    async def test_cache_miss_stores_result(self) -> None:
        """Should store result in cache on cache miss."""
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=create_groq_response("Fresh response"),
            )
        )

        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_client=mock_redis,
            cache_enabled=True,
            cache_ttl=3600,
        )

        result = await client.generate("Hello")

        assert result.raw_response == "Fresh response"
        mock_redis.set.assert_called_once()
        # Verify TTL was passed
        call_kwargs = mock_redis.set.call_args
        assert call_kwargs[1]["ex"] == 3600

        await client.shutdown()

    @respx.mock
    async def test_cache_read_error_continues_to_api(self) -> None:
        """Should call API when cache read fails."""
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=create_groq_response("API response"),
            )
        )

        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Redis connection failed"))
        mock_redis.set = AsyncMock()

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_client=mock_redis,
            cache_enabled=True,
        )

        result = await client.generate("Hello")

        assert result.raw_response == "API response"

        await client.shutdown()

    @respx.mock
    async def test_cache_write_error_continues(self) -> None:
        """Should return result even when cache write fails."""
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=create_groq_response("API response"),
            )
        )

        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(side_effect=Exception("Redis write failed"))

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_client=mock_redis,
            cache_enabled=True,
        )

        result = await client.generate("Hello")

        assert result.raw_response == "API response"

        await client.shutdown()

    @respx.mock
    async def test_skip_cache_bypasses_cache(self) -> None:
        """Should not use cache when skip_cache=True."""
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=create_groq_response("Fresh response"),
            )
        )

        mock_redis = MagicMock()
        mock_redis.get = AsyncMock()
        mock_redis.set = AsyncMock()

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_client=mock_redis,
            cache_enabled=True,
        )

        result = await client.generate("Hello", skip_cache=True)

        assert result.raw_response == "Fresh response"
        # Cache should not be read or written
        mock_redis.get.assert_not_called()
        mock_redis.set.assert_not_called()

        await client.shutdown()

    @respx.mock
    async def test_cache_json_decode_error(self) -> None:
        """Should call API when cached data is corrupted."""
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=create_groq_response("API response"),
            )
        )

        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value="not valid json")
        mock_redis.set = AsyncMock()

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_client=mock_redis,
            cache_enabled=True,
        )

        result = await client.generate("Hello")

        assert result.raw_response == "API response"

        await client.shutdown()


class TestGroqClientGenerateStructured:
    """Tests for generate_structured method."""

    @respx.mock
    async def test_generate_structured_returns_model(self) -> None:
        """Should return parsed model directly."""
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=create_groq_response('{"title": "Test", "items": ["x", "y"]}'),
            )
        )

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
        )

        result = await client.generate_structured("Extract", schema=SampleSchema)

        assert isinstance(result, SampleSchema)
        assert result.title == "Test"
        assert result.items == ["x", "y"]

        await client.shutdown()

    @respx.mock
    async def test_generate_structured_validation_error(self) -> None:
        """Should raise validation error when schema doesn't match."""
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=create_groq_response("invalid json"),
            )
        )

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
        )

        with pytest.raises(LLMValidationError):
            await client.generate_structured("Extract", schema=SampleSchema)

        await client.shutdown()

    @respx.mock
    async def test_generate_structured_null_parsed_raises(self) -> None:
        """Should raise LLMValidationError when parsed result is None."""
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=create_groq_response('{"title": "Test", "items": ["a"]}'),
            )
        )

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
        )

        # Mock generate to return a result with parsed=None
        mock_result = LLMCompletionResult(
            raw_response="some response",
            parsed=None,
            model="llama-3.1-8b-instant",
            prompt_tokens=10,
            completion_tokens=5,
            cached=False,
        )

        with (
            patch.object(client, "generate", new=AsyncMock(return_value=mock_result)),
            pytest.raises(LLMValidationError, match="no parsed result"),
        ):
            await client.generate_structured("Extract", schema=SampleSchema)

        await client.shutdown()


class TestGroqClientRetryExhaustion:
    """Tests for retry exhaustion scenarios."""

    @respx.mock
    async def test_max_retries_exceeded_timeout(self) -> None:
        """Should raise LLMTimeoutError after max retries on timeout."""
        timeout_msg = "Connection timed out"
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            side_effect=httpx.TimeoutException(timeout_msg)
        )

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
            max_retries=2,
        )

        with pytest.raises(LLMTimeoutError, match="timeout"):
            await client.generate("Hello")

        await client.shutdown()

    @respx.mock
    async def test_max_retries_exceeded_connection_error(self) -> None:
        """Should raise LLMUnavailableError after max retries on connection error."""
        call_count = 0

        def response_handler(_request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            msg = "Connection refused"
            raise httpx.ConnectError(msg)

        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            side_effect=response_handler
        )

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
            max_retries=2,
        )

        with pytest.raises(LLMUnavailableError, match="Cannot connect"):
            await client.generate("Hello")

        # Should have tried 3 times (initial + 2 retries)
        assert call_count == 3

        await client.shutdown()


class TestGroqClientOptions:
    """Tests for generate options handling."""

    @respx.mock
    async def test_generate_with_options(self) -> None:
        """Should pass temperature and max_tokens from options."""
        route = respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=create_groq_response("Response"),
            )
        )

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
        )

        await client.generate(
            "Hello",
            options={"temperature": 0.7, "num_predict": 100},
        )

        request_body = json.loads(route.calls[0].request.content)
        assert request_body["temperature"] == 0.7
        assert request_body["max_tokens"] == 100

        await client.shutdown()

    @respx.mock
    async def test_generate_with_system_and_schema(self) -> None:
        """Should combine system prompt with schema instruction."""
        route = respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=create_groq_response('{"title": "Test", "items": ["x"]}'),
            )
        )

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
        )

        await client.generate(
            "Extract data",
            system="You are a helpful assistant",
            schema=SampleSchema,
        )

        request_body = json.loads(route.calls[0].request.content)
        system_message = request_body["messages"][0]
        assert system_message["role"] == "system"
        # Should contain both the custom system prompt and schema instruction
        assert "helpful assistant" in system_message["content"]
        assert "JSON" in system_message["content"]
        assert "title" in system_message["content"]

        await client.shutdown()

    @respx.mock
    async def test_generate_auto_initializes(self) -> None:
        """Should auto-initialize when generate is called without explicit init."""
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=create_groq_response("Response"),
            )
        )

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
        )

        # Don't call initialize explicitly
        assert client._http_client is None

        result = await client.generate("Hello")

        # Should have auto-initialized
        assert client._http_client is not None
        assert result.raw_response == "Response"

        await client.shutdown()

    @respx.mock
    async def test_generate_with_custom_model(self) -> None:
        """Should use custom model when specified."""
        route = respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=create_groq_response("Response"),
            )
        )

        client = GroqClient(
            requests_per_minute=TEST_RATE_LIMIT,
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
        )

        await client.generate("Hello", model="mixtral-8x7b-32768")

        request_body = json.loads(route.calls[0].request.content)
        assert request_body["model"] == "mixtral-8x7b-32768"

        await client.shutdown()
