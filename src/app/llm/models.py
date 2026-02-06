"""LLM client data models.

This module defines request/response models for LLM interactions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OllamaGenerateRequest(BaseModel):
    """Request body for Ollama /api/generate endpoint."""

    model: str = Field(..., description="Model name (e.g., 'mistral:7b')")
    prompt: str = Field(..., description="Input prompt text")
    stream: bool = Field(default=False, description="Whether to stream response")
    format: str | dict[str, Any] | None = Field(
        default=None,
        description="Response format: 'json' or JSON schema dict",
    )
    options: dict[str, Any] | None = Field(
        default=None,
        description="Model-specific options (temperature, etc.)",
    )
    system: str | None = Field(
        default=None,
        description="System prompt to set context",
    )
    context: list[int] | None = Field(
        default=None,
        description="Context from previous request for conversation",
    )


class OllamaGenerateResponse(BaseModel):
    """Response from Ollama /api/generate endpoint."""

    model: str = Field(..., description="Model that generated response")
    created_at: str = Field(..., description="Timestamp of generation")
    response: str = Field(..., description="Generated text response")
    done: bool = Field(..., description="Whether generation is complete")
    context: list[int] | None = Field(
        default=None,
        description="Context for follow-up requests",
    )
    total_duration: int | None = Field(
        default=None,
        description="Total time in nanoseconds",
    )
    load_duration: int | None = Field(
        default=None,
        description="Model load time in nanoseconds",
    )
    prompt_eval_count: int | None = Field(
        default=None,
        description="Number of tokens in prompt",
    )
    prompt_eval_duration: int | None = Field(
        default=None,
        description="Time spent evaluating prompt",
    )
    eval_count: int | None = Field(
        default=None,
        description="Number of tokens generated",
    )
    eval_duration: int | None = Field(
        default=None,
        description="Time spent generating",
    )


class LLMCompletionResult(BaseModel):
    """Internal result from LLM completion.

    Wraps raw response with parsed structured output.
    """

    raw_response: str = Field(..., description="Raw text response from LLM")
    parsed: Any | None = Field(
        default=None,
        description="Parsed structured output if schema was provided",
    )
    model: str = Field(..., description="Model that generated response")
    prompt_tokens: int | None = Field(default=None, description="Input token count")
    completion_tokens: int | None = Field(
        default=None, description="Output token count"
    )
    cached: bool = Field(default=False, description="Whether response was from cache")

    model_config = {"frozen": True}


# =============================================================================
# Groq API Models (OpenAI-compatible chat format)
# =============================================================================


class GroqMessage(BaseModel):
    """Single message in Groq chat format."""

    role: str = Field(..., description="Message role: system, user, or assistant")
    content: str = Field(..., description="Message content")


class GroqChatRequest(BaseModel):
    """Request body for Groq /chat/completions endpoint."""

    model: str = Field(..., description="Model name (e.g., 'llama-3.1-8b-instant')")
    messages: list[dict[str, str]] = Field(..., description="Chat messages")
    response_format: dict[str, str] | None = Field(
        default=None,
        description="Response format: {'type': 'json_object'} for JSON mode",
    )
    temperature: float = Field(default=0.1, description="Sampling temperature")
    max_tokens: int | None = Field(
        default=None,
        description="Maximum tokens to generate",
    )
    stream: bool = Field(default=False, description="Whether to stream response")


class GroqUsage(BaseModel):
    """Token usage from Groq response."""

    prompt_tokens: int = Field(..., description="Input token count")
    completion_tokens: int = Field(..., description="Output token count")
    total_tokens: int = Field(..., description="Total token count")


class GroqChoice(BaseModel):
    """Single choice in Groq response."""

    index: int = Field(..., description="Choice index")
    message: GroqMessage = Field(..., description="Generated message")
    finish_reason: str = Field(..., description="Reason for completion")


class GroqChatResponse(BaseModel):
    """Response from Groq /chat/completions endpoint."""

    id: str = Field(..., description="Unique response ID")
    model: str = Field(..., description="Model that generated response")
    choices: list[GroqChoice] = Field(..., description="Generated completions")
    usage: GroqUsage = Field(..., description="Token usage statistics")
    created: int = Field(..., description="Unix timestamp of creation")
