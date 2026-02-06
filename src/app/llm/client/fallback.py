"""Fallback LLM client that chains multiple providers.

Tries primary provider first, falls back to secondary on LLMUnavailableError.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel

from app.llm.exceptions import LLMUnavailableError
from app.observability.logging import get_logger


if TYPE_CHECKING:
    from app.llm.client.protocol import LLMClientProtocol
    from app.llm.models import LLMCompletionResult


logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class FallbackLLMClient:
    """LLM client with automatic fallback to secondary provider.

    Orchestrates primary (e.g., Ollama) and secondary (e.g., Groq) clients.
    Falls back to secondary when primary raises LLMUnavailableError.

    Fallback triggers:
    - LLMUnavailableError: Connection refused, network errors
    - LLMTimeoutError: Request timeout (subclass of LLMUnavailableError)

    Non-fallback errors (propagated immediately):
    - LLMValidationError: Schema mismatch (retrying won't help)
    - LLMResponseError: HTTP 4xx/5xx errors
    - LLMRateLimitError: Should implement backoff, not fallback

    Example:
        ```python
        client = FallbackLLMClient(
            primary=OllamaClient(...),
            secondary=GroqClient(...),
        )
        result = await client.generate("prompt")  # Tries Ollama, then Groq
        ```
    """

    def __init__(
        self,
        primary: LLMClientProtocol,
        secondary: LLMClientProtocol | None = None,
        *,
        fallback_enabled: bool = True,
    ) -> None:
        """Initialize the fallback client.

        Args:
            primary: Primary LLM client (typically local Ollama).
            secondary: Fallback LLM client (typically cloud Groq).
            fallback_enabled: Master switch for fallback behavior.
        """
        self.primary = primary
        self.secondary = secondary
        self.fallback_enabled = fallback_enabled

    async def initialize(self) -> None:
        """Initialize both clients."""
        await self.primary.initialize()
        if self.secondary is not None:
            await self.secondary.initialize()
        logger.info(
            "FallbackLLMClient initialized",
            has_secondary=self.secondary is not None,
            fallback_enabled=self.fallback_enabled,
        )

    async def shutdown(self) -> None:
        """Shutdown both clients."""
        await self.primary.shutdown()
        if self.secondary is not None:
            await self.secondary.shutdown()
        logger.debug("FallbackLLMClient shutdown")

    async def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        schema: type[T] | None = None,
        options: dict[str, Any] | None = None,
        skip_cache: bool = False,
        context: str | None = None,
    ) -> LLMCompletionResult:
        """Generate with automatic fallback on unavailability.

        Tries primary client first. If it raises LLMUnavailableError
        and fallback is enabled with a secondary client, retries
        with the secondary client.

        Args:
            prompt: Input prompt text.
            model: Model override (uses client default if None).
            system: Optional system prompt.
            schema: Optional Pydantic model for structured JSON output.
            options: Model-specific options (temperature, etc.).
            skip_cache: Bypass cache if True.
            context: Optional context identifier for logging/tracing.

        Returns:
            LLMCompletionResult with raw_response and optionally parsed output.

        Raises:
            LLMUnavailableError: If both primary and secondary fail.
            LLMValidationError: If response doesn't match schema.
            LLMResponseError: If service returns HTTP error.
        """
        try:
            return await self.primary.generate(
                prompt=prompt,
                model=model,
                system=system,
                schema=schema,
                options=options,
                skip_cache=skip_cache,
                context=context,
            )
        except LLMUnavailableError as e:
            if not self.fallback_enabled or self.secondary is None:
                logger.exception(
                    "Primary LLM unavailable, no fallback configured",
                    context=context,
                )
                raise

            logger.warning(
                "Primary LLM unavailable, falling back to secondary",
                context=context,
                primary_error=str(e),
            )

            return await self.secondary.generate(
                prompt=prompt,
                model=model,
                system=system,
                schema=schema,
                options=options,
                skip_cache=skip_cache,
                context=context,
            )

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        model: str | None = None,
        system: str | None = None,
        options: dict[str, Any] | None = None,
        skip_cache: bool = False,
        context: str | None = None,
    ) -> T:
        """Generate structured output with fallback.

        Args:
            prompt: Input prompt text.
            schema: Pydantic model class for output structure.
            model: Model to use (defaults to client's default model).
            system: Optional system prompt for context.
            options: Model-specific options.
            skip_cache: If True, bypass cache for this request.
            context: Optional context identifier for logging/tracing.

        Returns:
            Instance of the schema class populated from LLM response.

        Raises:
            LLMUnavailableError: If both primary and secondary fail.
            LLMValidationError: If response doesn't match schema.
        """
        try:
            return await self.primary.generate_structured(
                prompt=prompt,
                schema=schema,
                model=model,
                system=system,
                options=options,
                skip_cache=skip_cache,
                context=context,
            )
        except LLMUnavailableError as e:
            if not self.fallback_enabled or self.secondary is None:
                logger.exception(
                    "Primary LLM unavailable, no fallback configured",
                    context=context,
                )
                raise

            logger.warning(
                "Primary LLM unavailable, falling back to secondary",
                context=context,
                primary_error=str(e),
            )

            return await self.secondary.generate_structured(
                prompt=prompt,
                schema=schema,
                model=model,
                system=system,
                options=options,
                skip_cache=skip_cache,
                context=context,
            )
