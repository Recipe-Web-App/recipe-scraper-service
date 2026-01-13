"""HTTP client for Ollama LLM service.

This module provides an async HTTP client for communicating with
a local or remote Ollama instance for LLM inference.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any, TypeVar, cast

import httpx
from pydantic import BaseModel

from app.llm.exceptions import (
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    LLMUnavailableError,
    LLMValidationError,
)
from app.llm.models import (
    LLMCompletionResult,
    OllamaGenerateRequest,
    OllamaGenerateResponse,
)
from app.observability.logging import get_logger


if TYPE_CHECKING:
    from redis.asyncio import Redis


logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class OllamaClient:
    """Async HTTP client for Ollama LLM service.

    Provides methods for:
    - Text generation with structured JSON output
    - Response caching in Redis
    - Automatic retries for transient failures

    The client supports connection pooling and configurable timeouts
    suitable for long-running LLM inference requests.

    Attributes:
        base_url: Base URL of the Ollama service.
        model: Default model to use for generation.
        timeout: HTTP request timeout in seconds.
        max_retries: Maximum retry attempts for transient failures.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float = 60.0,
        max_retries: int = 2,
        cache_client: Redis[Any] | None = None,
        cache_ttl: int = 3600,
        cache_enabled: bool = True,
    ) -> None:
        """Initialize the Ollama client.

        Args:
            base_url: Base URL of Ollama service (e.g., http://localhost:11434).
            model: Default model name (e.g., mistral:7b).
            timeout: HTTP request timeout in seconds (default: 60).
            max_retries: Maximum retries for transient failures (default: 2).
            cache_client: Optional Redis client for caching responses.
            cache_ttl: Cache TTL in seconds (default: 3600 = 1 hour).
            cache_enabled: Whether to use caching (default: True).
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.cache_client = cache_client
        self.cache_ttl = cache_ttl
        self.cache_enabled = cache_enabled
        self._http_client: httpx.AsyncClient | None = None

    @property
    def generate_url(self) -> str:
        """Get the generate endpoint URL."""
        return f"{self.base_url}/api/generate"

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
            "OllamaClient initialized",
            base_url=self.base_url,
            model=self.model,
            timeout=self.timeout,
        )

    async def shutdown(self) -> None:
        """Close the HTTP client and release connections."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
            logger.debug("OllamaClient shutdown")

    def _get_cache_key(
        self,
        prompt: str,
        model: str,
        schema: type[BaseModel] | None,
        system: str | None,
    ) -> str:
        """Generate cache key for a prompt.

        Uses a hash of the prompt + model + schema to create reproducible keys.
        """
        schema_str = str(schema.model_json_schema()) if schema else ""
        content = f"{model}:{system or ''}:{prompt}:{schema_str}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"llm:generate:{content_hash}"

    async def _get_cached_result(
        self,
        cache_key: str,
    ) -> LLMCompletionResult | None:
        """Get cached completion result if available."""
        if not self.cache_enabled or not self.cache_client:
            return None

        try:
            cached = await self.cache_client.get(cache_key)
            if cached:
                logger.debug("Cache hit for LLM completion", cache_key=cache_key)
                result = LLMCompletionResult.model_validate_json(cached)
                # Return with cached=True flag
                return LLMCompletionResult(
                    raw_response=result.raw_response,
                    parsed=result.parsed,
                    model=result.model,
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    cached=True,
                )
        except Exception as e:
            logger.warning("Failed to read from LLM cache", error=str(e))

        return None

    async def _cache_result(
        self,
        cache_key: str,
        result: LLMCompletionResult,
    ) -> None:
        """Cache a completion result."""
        if not self.cache_enabled or not self.cache_client:
            return

        try:
            await self.cache_client.set(
                cache_key,
                result.model_dump_json(),
                ex=self.cache_ttl,
            )
            logger.debug(
                "Cached LLM completion", cache_key=cache_key, ttl=self.cache_ttl
            )
        except Exception as e:
            logger.warning("Failed to cache LLM completion", error=str(e))

    async def _execute_with_retry(
        self,
        request: OllamaGenerateRequest,
    ) -> OllamaGenerateResponse:
        """Execute request with retry logic for transient failures."""
        if self._http_client is None:
            await self.initialize()

        assert self._http_client is not None

        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._http_client.post(
                    self.generate_url,
                    json=request.model_dump(exclude_none=True),
                )

                if response.status_code == 429:
                    msg = "Ollama rate limit exceeded"
                    raise LLMRateLimitError(msg)

                response.raise_for_status()
                return OllamaGenerateResponse.model_validate(response.json())

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(
                    "Ollama request timeout",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    timeout=self.timeout,
                )
                if attempt < self.max_retries:
                    continue
                msg = f"Ollama timeout after {self.timeout}s"
                raise LLMTimeoutError(msg) from e

            except httpx.HTTPStatusError as e:
                logger.exception(
                    "Ollama request failed",
                    status_code=e.response.status_code,
                    url=self.generate_url,
                )
                msg = f"Ollama returned {e.response.status_code}"
                raise LLMResponseError(msg) from e

            except httpx.RequestError as e:
                last_exception = e
                logger.warning(
                    "Ollama connection error",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    error=str(e),
                )
                if attempt < self.max_retries:
                    continue
                msg = f"Cannot connect to Ollama: {e}"
                raise LLMUnavailableError(msg) from e

        # Should not reach here, but satisfy type checker
        msg = "Max retries exceeded"
        raise LLMUnavailableError(msg) from last_exception

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
            model: Model to use (defaults to client's default model).
            system: Optional system prompt for context.
            schema: Optional Pydantic model for structured JSON output.
            options: Model-specific options (temperature, top_p, etc.).
            skip_cache: If True, bypass cache for this request.

        Returns:
            LLMCompletionResult with raw response and optionally parsed output.

        Raises:
            LLMUnavailableError: If Ollama cannot be reached.
            LLMTimeoutError: If request times out.
            LLMResponseError: If Ollama returns an error.
            LLMValidationError: If response doesn't match schema.
        """
        use_model = model or self.model

        # Check cache first
        cache_key = self._get_cache_key(prompt, use_model, schema, system)
        if not skip_cache:
            cached = await self._get_cached_result(cache_key)
            if cached is not None:
                return cached

        # Build request with optional structured output format
        format_spec: str | dict[str, Any] | None = None
        if schema is not None:
            format_spec = schema.model_json_schema()

        request = OllamaGenerateRequest(
            model=use_model,
            prompt=prompt,
            stream=False,
            format=format_spec,
            options=options,
            system=system,
        )

        # Execute with retry
        response = await self._execute_with_retry(request)

        # Parse structured output if schema provided
        parsed: Any = None
        if schema is not None:
            try:
                parsed = schema.model_validate_json(response.response)
            except Exception as e:
                logger.warning(
                    "Failed to parse structured LLM output",
                    schema=schema.__name__,
                    error=str(e),
                    raw_response=response.response[:500],
                )
                msg = f"Response does not match {schema.__name__} schema: {e}"
                raise LLMValidationError(msg) from e

        result = LLMCompletionResult(
            raw_response=response.response,
            parsed=parsed,
            model=response.model,
            prompt_tokens=response.prompt_eval_count,
            completion_tokens=response.eval_count,
            cached=False,
        )

        # Cache the result
        if not skip_cache:
            await self._cache_result(cache_key, result)

        return result

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

        Convenience method that returns the parsed result directly.

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
        result = await self.generate(
            prompt=prompt,
            model=model,
            system=system,
            schema=schema,
            options=options,
            skip_cache=skip_cache,
        )

        if result.parsed is None:
            msg = "Structured generation returned no parsed result"
            raise LLMValidationError(msg)

        return cast("T", result.parsed)
