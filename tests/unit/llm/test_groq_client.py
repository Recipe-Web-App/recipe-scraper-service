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
from tests.fixtures.llm_responses import create_groq_response


pytestmark = pytest.mark.unit


class SampleSchema(BaseModel):
    """Sample schema for testing structured output."""

    title: str
    items: list[str]


class TestGroqClientInitialization:
    """Tests for client initialization and lifecycle."""

    async def test_initialize_creates_http_client(self) -> None:
        """Should create HTTP client on initialize."""
        client = GroqClient(
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
        )

        await client.initialize()

        assert client._http_client is not None
        await client.shutdown()

    async def test_shutdown_closes_http_client(self) -> None:
        """Should close HTTP client on shutdown."""
        client = GroqClient(
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
        )

        await client.initialize()
        await client.shutdown()

        assert client._http_client is None

    async def test_initialize_idempotent(self) -> None:
        """Should be safe to call initialize multiple times."""
        client = GroqClient(
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
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
        )

        assert client.chat_url == "https://api.groq.com/openai/v1/chat/completions"

    def test_chat_url_custom(self) -> None:
        """Should allow custom base URL."""
        client = GroqClient(
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
            return_value=httpx.Response(429, headers={"retry-after": "60"})
        )

        client = GroqClient(
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
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
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
            max_retries=2,
        )

        with pytest.raises(LLMResponseError):
            await client.generate("Hello")

        assert call_count == 1

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
            api_key="test-api-key",
            model="llama-3.1-8b-instant",
            cache_enabled=False,
        )

        with pytest.raises(LLMValidationError):
            await client.generate_structured("Extract", schema=SampleSchema)

        await client.shutdown()
