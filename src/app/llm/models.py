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
