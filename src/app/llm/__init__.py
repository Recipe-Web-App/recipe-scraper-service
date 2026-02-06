"""LLM integration module.

Provides a client for communicating with local LLM services (Ollama)
for tasks like recipe parsing, ingredient extraction, and recommendations.
"""

from app.llm.client.ollama import OllamaClient
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    LLMUnavailableError,
    LLMValidationError,
)
from app.llm.models import LLMCompletionResult
from app.llm.prompts.base import BasePrompt


__all__ = [
    "BasePrompt",
    "LLMCompletionResult",
    "LLMConfigurationError",
    "LLMError",
    "LLMRateLimitError",
    "LLMResponseError",
    "LLMTimeoutError",
    "LLMUnavailableError",
    "LLMValidationError",
    "OllamaClient",
]
