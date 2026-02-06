"""LLM client exceptions.

This module defines exceptions specific to LLM client operations.
These exceptions are caught by the service layer and converted to
appropriate HTTP responses or fallback behaviors.
"""

from __future__ import annotations


class LLMError(Exception):
    """Base exception for LLM client errors."""


class LLMUnavailableError(LLMError):
    """Raised when the LLM service cannot be reached.

    This includes connection errors, timeouts, and service unavailability.
    Should trigger retry logic or graceful degradation.
    """


class LLMTimeoutError(LLMUnavailableError):
    """Raised when an LLM request times out.

    Inherits from LLMUnavailableError since timeouts are a form of
    service unavailability that may warrant retries.
    """


class LLMResponseError(LLMError):
    """Raised when the LLM returns an error response.

    This includes HTTP 4xx/5xx errors from the LLM service.
    """


class LLMValidationError(LLMError):
    """Raised when LLM response fails schema validation.

    The LLM returned a response, but it doesn't conform to the
    expected structured output schema.
    """


class LLMRateLimitError(LLMError):
    """Raised when the LLM service rate limits the request."""


class LLMConfigurationError(LLMError):
    """Raised when the LLM client is misconfigured."""
