"""Unit tests for FallbackLLMClient.

Tests cover:
- Fallback triggering logic
- Error propagation
- Lifecycle management
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from app.llm.client.fallback import FallbackLLMClient
from app.llm.exceptions import (
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    LLMUnavailableError,
    LLMValidationError,
)
from app.llm.models import LLMCompletionResult


pytestmark = pytest.mark.unit


class SampleSchema(BaseModel):
    """Test schema for structured output tests."""

    value: str


def create_mock_client(
    generate_result: LLMCompletionResult | None = None,
    generate_error: Exception | None = None,
    structured_result: BaseModel | None = None,
    structured_error: Exception | None = None,
) -> MagicMock:
    """Create a mock LLM client for testing."""
    mock = MagicMock()
    mock.initialize = AsyncMock()
    mock.shutdown = AsyncMock()

    if generate_error:
        mock.generate = AsyncMock(side_effect=generate_error)
    else:
        mock.generate = AsyncMock(
            return_value=generate_result
            or LLMCompletionResult(
                raw_response="Default response",
                model="test-model",
                parsed=None,
            )
        )

    if structured_error:
        mock.generate_structured = AsyncMock(side_effect=structured_error)
    else:
        mock.generate_structured = AsyncMock(
            return_value=structured_result or SampleSchema(value="default")
        )

    return mock


class TestFallbackBehavior:
    """Tests for fallback triggering logic."""

    async def test_uses_primary_when_available(self) -> None:
        """Should use primary client when it succeeds."""
        primary_result = LLMCompletionResult(
            raw_response="Primary response",
            model="mistral:7b",
            parsed=None,
        )
        primary = create_mock_client(generate_result=primary_result)
        secondary = create_mock_client()

        client = FallbackLLMClient(primary=primary, secondary=secondary)
        await client.initialize()

        result = await client.generate("test")

        assert result.raw_response == "Primary response"
        primary.generate.assert_called_once()
        secondary.generate.assert_not_called()

        await client.shutdown()

    async def test_falls_back_on_unavailable_error(self) -> None:
        """Should fall back to secondary on LLMUnavailableError."""
        primary = create_mock_client(
            generate_error=LLMUnavailableError("Connection refused")
        )
        secondary_result = LLMCompletionResult(
            raw_response="Fallback response",
            model="llama-3.1-8b-instant",
            parsed=None,
        )
        secondary = create_mock_client(generate_result=secondary_result)

        client = FallbackLLMClient(primary=primary, secondary=secondary)
        await client.initialize()

        result = await client.generate("test")

        assert result.raw_response == "Fallback response"
        primary.generate.assert_called_once()
        secondary.generate.assert_called_once()

        await client.shutdown()

    async def test_falls_back_on_timeout_error(self) -> None:
        """Should fall back to secondary on LLMTimeoutError."""
        primary = create_mock_client(generate_error=LLMTimeoutError("Timeout"))
        secondary_result = LLMCompletionResult(
            raw_response="Fallback",
            model="model",
            parsed=None,
        )
        secondary = create_mock_client(generate_result=secondary_result)

        client = FallbackLLMClient(primary=primary, secondary=secondary)
        await client.initialize()

        result = await client.generate("test")

        assert result.raw_response == "Fallback"

        await client.shutdown()

    async def test_no_fallback_on_validation_error(self) -> None:
        """Should NOT fall back on LLMValidationError."""
        primary = create_mock_client(
            generate_error=LLMValidationError("Schema mismatch")
        )
        secondary = create_mock_client()

        client = FallbackLLMClient(primary=primary, secondary=secondary)
        await client.initialize()

        with pytest.raises(LLMValidationError):
            await client.generate("test")

        secondary.generate.assert_not_called()

        await client.shutdown()

    async def test_no_fallback_on_response_error(self) -> None:
        """Should NOT fall back on LLMResponseError."""
        primary = create_mock_client(generate_error=LLMResponseError("HTTP 500"))
        secondary = create_mock_client()

        client = FallbackLLMClient(primary=primary, secondary=secondary)
        await client.initialize()

        with pytest.raises(LLMResponseError):
            await client.generate("test")

        secondary.generate.assert_not_called()

        await client.shutdown()

    async def test_no_fallback_on_rate_limit_error(self) -> None:
        """Should NOT fall back on LLMRateLimitError."""
        primary = create_mock_client(generate_error=LLMRateLimitError("Rate limited"))
        secondary = create_mock_client()

        client = FallbackLLMClient(primary=primary, secondary=secondary)
        await client.initialize()

        with pytest.raises(LLMRateLimitError):
            await client.generate("test")

        secondary.generate.assert_not_called()

        await client.shutdown()

    async def test_raises_when_no_secondary_configured(self) -> None:
        """Should raise original error when secondary not configured."""
        primary = create_mock_client(generate_error=LLMUnavailableError("Down"))

        client = FallbackLLMClient(primary=primary, secondary=None)
        await client.initialize()

        with pytest.raises(LLMUnavailableError):
            await client.generate("test")

        await client.shutdown()

    async def test_raises_when_fallback_disabled(self) -> None:
        """Should raise original error when fallback disabled."""
        primary = create_mock_client(generate_error=LLMUnavailableError("Down"))
        secondary = create_mock_client()

        client = FallbackLLMClient(
            primary=primary,
            secondary=secondary,
            fallback_enabled=False,
        )
        await client.initialize()

        with pytest.raises(LLMUnavailableError):
            await client.generate("test")

        secondary.generate.assert_not_called()

        await client.shutdown()

    async def test_both_fail_raises_secondary_error(self) -> None:
        """Should raise secondary error when both fail."""
        primary = create_mock_client(generate_error=LLMUnavailableError("Primary down"))
        secondary = create_mock_client(
            generate_error=LLMUnavailableError("Secondary down")
        )

        client = FallbackLLMClient(primary=primary, secondary=secondary)
        await client.initialize()

        with pytest.raises(LLMUnavailableError, match="Secondary down"):
            await client.generate("test")

        await client.shutdown()


class TestGenerateStructuredFallback:
    """Tests for generate_structured fallback."""

    async def test_structured_uses_primary(self) -> None:
        """Should use primary for structured generation."""
        primary_result = SampleSchema(value="primary")
        primary = create_mock_client(structured_result=primary_result)
        secondary = create_mock_client()

        client = FallbackLLMClient(primary=primary, secondary=secondary)
        await client.initialize()

        result = await client.generate_structured("test", schema=SampleSchema)

        assert result.value == "primary"
        primary.generate_structured.assert_called_once()
        secondary.generate_structured.assert_not_called()

        await client.shutdown()

    async def test_structured_falls_back_correctly(self) -> None:
        """Should fall back for structured generation too."""
        primary = create_mock_client(structured_error=LLMUnavailableError("Down"))
        secondary_result = SampleSchema(value="fallback")
        secondary = create_mock_client(structured_result=secondary_result)

        client = FallbackLLMClient(primary=primary, secondary=secondary)
        await client.initialize()

        result = await client.generate_structured("test", schema=SampleSchema)

        assert result.value == "fallback"

        await client.shutdown()

    async def test_structured_no_fallback_on_validation_error(self) -> None:
        """Should NOT fall back on validation error for structured."""
        primary = create_mock_client(
            structured_error=LLMValidationError("Schema mismatch")
        )
        secondary = create_mock_client()

        client = FallbackLLMClient(primary=primary, secondary=secondary)
        await client.initialize()

        with pytest.raises(LLMValidationError):
            await client.generate_structured("test", schema=SampleSchema)

        secondary.generate_structured.assert_not_called()

        await client.shutdown()


class TestLifecycle:
    """Tests for client lifecycle management."""

    async def test_initialize_initializes_both_clients(self) -> None:
        """Should initialize both primary and secondary."""
        primary = create_mock_client()
        secondary = create_mock_client()

        client = FallbackLLMClient(primary=primary, secondary=secondary)
        await client.initialize()

        primary.initialize.assert_called_once()
        secondary.initialize.assert_called_once()

        await client.shutdown()

    async def test_initialize_only_primary_when_no_secondary(self) -> None:
        """Should only initialize primary when no secondary."""
        primary = create_mock_client()

        client = FallbackLLMClient(primary=primary, secondary=None)
        await client.initialize()

        primary.initialize.assert_called_once()

        await client.shutdown()

    async def test_shutdown_shuts_down_both_clients(self) -> None:
        """Should shutdown both primary and secondary."""
        primary = create_mock_client()
        secondary = create_mock_client()

        client = FallbackLLMClient(primary=primary, secondary=secondary)
        await client.initialize()
        await client.shutdown()

        primary.shutdown.assert_called_once()
        secondary.shutdown.assert_called_once()

    async def test_shutdown_only_primary_when_no_secondary(self) -> None:
        """Should only shutdown primary when no secondary."""
        primary = create_mock_client()

        client = FallbackLLMClient(primary=primary, secondary=None)
        await client.initialize()
        await client.shutdown()

        primary.shutdown.assert_called_once()


class TestArgumentPassthrough:
    """Tests for argument passthrough to underlying clients."""

    async def test_generate_passes_all_arguments(self) -> None:
        """Should pass all arguments to primary client."""
        primary = create_mock_client()
        secondary = create_mock_client()

        client = FallbackLLMClient(primary=primary, secondary=secondary)
        await client.initialize()

        await client.generate(
            "test prompt",
            model="custom-model",
            system="system prompt",
            schema=SampleSchema,
            options={"temperature": 0.5},
            skip_cache=True,
        )

        primary.generate.assert_called_once_with(
            prompt="test prompt",
            model="custom-model",
            system="system prompt",
            schema=SampleSchema,
            options={"temperature": 0.5},
            skip_cache=True,
        )

        await client.shutdown()

    async def test_fallback_passes_same_arguments(self) -> None:
        """Should pass same arguments to secondary on fallback."""
        primary = create_mock_client(generate_error=LLMUnavailableError("Down"))
        secondary = create_mock_client()

        client = FallbackLLMClient(primary=primary, secondary=secondary)
        await client.initialize()

        await client.generate(
            "test prompt",
            model="custom-model",
            system="system prompt",
            options={"temperature": 0.5},
        )

        secondary.generate.assert_called_once_with(
            prompt="test prompt",
            model="custom-model",
            system="system prompt",
            schema=None,
            options={"temperature": 0.5},
            skip_cache=False,
        )

        await client.shutdown()
