"""HTTP client for Groq LLM service.

Groq provides fast cloud inference with an OpenAI-compatible API.
Used as a fallback when local Ollama is unavailable.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any, TypeVar, cast

import httpx
from aiolimiter import AsyncLimiter
from pydantic import BaseModel

from app.llm.exceptions import (
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    LLMUnavailableError,
    LLMValidationError,
)
from app.llm.models import (
    GroqChatRequest,
    GroqChatResponse,
    LLMCompletionResult,
)
from app.observability.logging import get_logger


if TYPE_CHECKING:
    from redis.asyncio import Redis


logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class GroqClient:
    """Async HTTP client for Groq LLM service.

    Provides OpenAI-compatible API access for cloud-based inference.
    Supports JSON mode for structured output via response_format.

    Attributes:
        base_url: Groq API base URL.
        model: Default model (e.g., llama-3.1-8b-instant).
        api_key: Groq API key for authentication.
        timeout: HTTP request timeout in seconds.
        max_retries: Maximum retry attempts for transient failures.
    """

    DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.1-8b-instant",
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 2,
        cache_client: Redis[Any] | None = None,
        cache_ttl: int = 3600,
        cache_enabled: bool = True,
        requests_per_minute: float = 30.0,
    ) -> None:
        """Initialize the Groq client.

        Args:
            api_key: Groq API key for authentication.
            model: Default model name (e.g., llama-3.1-8b-instant).
            base_url: Groq API base URL.
            timeout: HTTP request timeout in seconds (default: 30).
            max_retries: Maximum retries for transient failures (default: 2).
            cache_client: Optional Redis client for caching responses.
            cache_ttl: Cache TTL in seconds (default: 3600 = 1 hour).
            cache_enabled: Whether to use caching (default: True).
            requests_per_minute: Rate limit for API requests (default: 30, Groq free tier).
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.cache_client = cache_client
        self.cache_ttl = cache_ttl
        self.cache_enabled = cache_enabled
        self._http_client: httpx.AsyncClient | None = None
        # Prevent bursts: 1 request per (60/rpm) seconds instead of rpm requests per 60s
        # With 30 RPM: allows 1 request every 2 seconds (no initial burst)
        self._rate_limiter = AsyncLimiter(1, 60.0 / requests_per_minute)

    @property
    def chat_url(self) -> str:
        """Get the chat completions endpoint URL."""
        return f"{self.base_url}/chat/completions"

    async def initialize(self) -> None:
        """Initialize the HTTP client with auth headers."""
        if self._http_client is not None:
            return

        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
            ),
        )
        logger.info(
            "GroqClient initialized",
            model=self.model,
            timeout=self.timeout,
        )

    async def shutdown(self) -> None:
        """Close the HTTP client and release connections."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
            logger.debug("GroqClient shutdown")

    def _get_cache_key(
        self,
        prompt: str,
        model: str,
        schema: type[BaseModel] | None,
        system: str | None,
    ) -> str:
        """Generate cache key for a prompt.

        Uses a hash of the prompt + model + schema to create reproducible keys.
        Prefixed with 'groq:' to distinguish from other providers.
        """
        schema_str = str(schema.model_json_schema()) if schema else ""
        content = f"groq:{model}:{system or ''}:{prompt}:{schema_str}"
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
                logger.debug("Cache hit for Groq completion", cache_key=cache_key)
                result = LLMCompletionResult.model_validate_json(cached)
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
                "Cached Groq completion", cache_key=cache_key, ttl=self.cache_ttl
            )
        except Exception as e:
            logger.warning("Failed to cache Groq completion", error=str(e))

    async def _execute_with_retry(
        self,
        request: GroqChatRequest,
    ) -> GroqChatResponse:
        """Execute request with retry logic for transient failures."""
        if self._http_client is None:
            await self.initialize()

        assert self._http_client is not None

        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            # Wait for rate limiter before making request
            await self._rate_limiter.acquire()

            try:
                response = await self._http_client.post(
                    self.chat_url,
                    json=request.model_dump(exclude_none=True),
                )

                if response.status_code == 429:
                    retry_after = response.headers.get("retry-after", "60")
                    msg = f"Groq rate limit exceeded, retry after {retry_after}s"
                    raise LLMRateLimitError(msg)

                response.raise_for_status()
                return GroqChatResponse.model_validate(response.json())

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(
                    "Groq request timeout",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    timeout=self.timeout,
                )
                if attempt < self.max_retries:
                    continue
                msg = f"Groq timeout after {self.timeout}s"
                raise LLMTimeoutError(msg) from e

            except httpx.HTTPStatusError as e:
                logger.exception(
                    "Groq request failed",
                    status_code=e.response.status_code,
                    url=self.chat_url,
                )
                msg = f"Groq returned {e.response.status_code}"
                raise LLMResponseError(msg) from e

            except httpx.RequestError as e:
                last_exception = e
                logger.warning(
                    "Groq connection error",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    error=str(e),
                )
                if attempt < self.max_retries:
                    continue
                msg = f"Cannot connect to Groq: {e}"
                raise LLMUnavailableError(msg) from e

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
        """Generate text completion from Groq.

        Args:
            prompt: Input prompt text.
            model: Model to use (defaults to client's default model).
            system: Optional system prompt for context.
            schema: Optional Pydantic model for structured JSON output.
            options: Model-specific options (temperature, etc.).
            skip_cache: If True, bypass cache for this request.

        Returns:
            LLMCompletionResult with raw response and optionally parsed output.

        Raises:
            LLMUnavailableError: If Groq cannot be reached.
            LLMTimeoutError: If request times out.
            LLMResponseError: If Groq returns an error.
            LLMValidationError: If response doesn't match schema.
        """
        use_model = model or self.model

        # Check cache first
        cache_key = self._get_cache_key(prompt, use_model, schema, system)
        if not skip_cache:
            cached = await self._get_cached_result(cache_key)
            if cached is not None:
                return cached

        # Build messages for chat API
        messages: list[dict[str, str]] = []

        # Handle system prompt and schema instruction
        system_content = system or ""
        if schema is not None:
            schema_instruction = (
                f"You must respond with valid JSON matching this schema: "
                f"{schema.model_json_schema()}"
            )
            if system_content:
                system_content = f"{system_content}\n\n{schema_instruction}"
            else:
                system_content = schema_instruction

        if system_content:
            messages.append({"role": "system", "content": system_content})

        messages.append({"role": "user", "content": prompt})

        # Configure JSON mode if schema provided
        response_format: dict[str, str] | None = None
        if schema is not None:
            response_format = {"type": "json_object"}

        # Extract options
        temperature = 0.1
        max_tokens = None
        if options:
            temperature = options.get("temperature", 0.1)
            max_tokens = options.get("num_predict")

        # Build request
        request = GroqChatRequest(
            model=use_model,
            messages=messages,
            response_format=response_format,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Execute with retry
        response = await self._execute_with_retry(request)

        raw_response = response.choices[0].message.content

        # Parse structured output if schema provided
        parsed: Any = None
        if schema is not None:
            try:
                parsed = schema.model_validate_json(raw_response)
            except Exception as e:
                logger.warning(
                    "Failed to parse structured Groq output",
                    schema=schema.__name__,
                    error=str(e),
                    raw_response=raw_response[:500],
                )
                msg = f"Response does not match {schema.__name__} schema: {e}"
                raise LLMValidationError(msg) from e

        result = LLMCompletionResult(
            raw_response=raw_response,
            parsed=parsed,
            model=response.model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
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
