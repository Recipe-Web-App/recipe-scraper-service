"""Base class for LLM prompts.

Provides a standardized interface for defining prompts with:
- Typed input variables
- Structured output schemas
- Model-specific configuration
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel


class BasePrompt[T: BaseModel](ABC):
    """Base class for all LLM prompts.

    Centralizes prompt definitions to:
    - Prevent scattered hardcoded strings
    - Enable prompt versioning and testing
    - Standardize input/output schemas
    - Configure model-specific options

    Example:
        ```python
        class RecipeExtractionPrompt(BasePrompt[ExtractedRecipe]):
            output_schema = ExtractedRecipe
            system_prompt = "You are a recipe extraction assistant."

            def format(self, html_content: str) -> str:
                return f"Extract recipe from:\\n\\n{html_content}"
        ```
    """

    # Override in subclasses
    output_schema: ClassVar[type[BaseModel]]
    """Pydantic model for structured output validation."""

    system_prompt: ClassVar[str | None] = None
    """Optional system prompt to set context for the LLM."""

    temperature: ClassVar[float] = 0.1
    """Temperature for generation (low = more deterministic)."""

    max_tokens: ClassVar[int | None] = None
    """Maximum tokens to generate (None = model default)."""

    @abstractmethod
    def format(self, **kwargs: Any) -> str:
        """Format the prompt template with input variables.

        Args:
            **kwargs: Variables to substitute into template.

        Returns:
            Formatted prompt string ready for LLM.

        Raises:
            ValueError: If required variables are missing.
        """
        ...

    @property
    def name(self) -> str:
        """Prompt identifier for logging and caching."""
        return self.__class__.__name__

    def get_options(self) -> dict[str, Any]:
        """Get model options for this prompt.

        Returns:
            Dict of options to pass to the LLM.
        """
        options: dict[str, Any] = {"temperature": self.temperature}
        if self.max_tokens is not None:
            options["num_predict"] = self.max_tokens
        return options
