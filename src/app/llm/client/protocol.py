"""LLM Client Protocol definition.

Defines the interface that all LLM clients must implement,
enabling interchangeable backends and fallback composition.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel


if TYPE_CHECKING:
    from app.llm.models import LLMCompletionResult


T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class LLMClientProtocol(Protocol):
    """Protocol for LLM client implementations.

    All LLM clients (Ollama, Groq, etc.) must implement this
    interface to enable composition in FallbackLLMClient.

    Key methods:
    - generate: Text generation with optional structured output
    - generate_structured: Convenience method returning parsed Pydantic model
    - initialize/shutdown: Lifecycle management for connection pools
    """

    async def initialize(self) -> None:
        """Initialize client resources (HTTP connections, etc.)."""
        ...

    async def shutdown(self) -> None:
        """Release client resources."""
        ...

    async def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        schema: type[T] | None = None,
        options: dict[str, Any] | None = None,
        skip_cache: bool = False,
    ) -> LLMCompletionResult:
        """Generate text completion from the LLM.

        Args:
            prompt: Input prompt text.
            model: Model override (uses client default if None).
            system: Optional system prompt.
            schema: Optional Pydantic model for structured JSON output.
            options: Model-specific options (temperature, etc.).
            skip_cache: Bypass cache if True.

        Returns:
            LLMCompletionResult with raw_response and optionally parsed output.

        Raises:
            LLMUnavailableError: Service unreachable (triggers fallback).
            LLMTimeoutError: Request timed out.
            LLMResponseError: HTTP error from service.
            LLMValidationError: Response doesn't match schema.
        """
        ...

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        model: str | None = None,
        system: str | None = None,
        options: dict[str, Any] | None = None,
        skip_cache: bool = False,
    ) -> T:
        """Generate structured output matching a Pydantic schema.

        Convenience method returning the parsed model directly.

        Args:
            prompt: Input prompt text.
            schema: Pydantic model class for output structure.
            model: Model to use (defaults to client's default model).
            system: Optional system prompt for context.
            options: Model-specific options.
            skip_cache: If True, bypass cache for this request.

        Returns:
            Instance of the schema class populated from LLM response.

        Raises:
            LLMValidationError: If response doesn't match schema.
        """
        ...
