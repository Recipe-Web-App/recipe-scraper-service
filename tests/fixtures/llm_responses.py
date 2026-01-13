"""Canned LLM responses for testing.

These responses were recorded from real Ollama interactions
and can be replayed in tests without GPU resources.
"""

from __future__ import annotations

from typing import Any


def create_ollama_response(
    content: str,
    model: str = "mistral:7b",
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
) -> dict[str, Any]:
    """Factory for creating mock Ollama responses."""
    return {
        "model": model,
        "created_at": "2024-01-15T10:30:00Z",
        "response": content,
        "done": True,
        "prompt_eval_count": prompt_tokens,
        "eval_count": completion_tokens,
        "total_duration": 8500000000,
        "load_duration": 1000000000,
        "prompt_eval_duration": 2000000000,
        "eval_duration": 5000000000,
    }


# Recipe extraction response
RECIPE_EXTRACTION_RESPONSE: dict[str, Any] = create_ollama_response(
    content="""{
    "title": "Classic Chocolate Chip Cookies",
    "ingredients": [
        {"name": "all-purpose flour", "amount": 2.25, "unit": "cups"},
        {"name": "butter", "amount": 1, "unit": "cup"},
        {"name": "sugar", "amount": 0.75, "unit": "cups"},
        {"name": "brown sugar", "amount": 0.75, "unit": "cups"},
        {"name": "eggs", "amount": 2, "unit": "large"},
        {"name": "vanilla extract", "amount": 1, "unit": "tsp"},
        {"name": "baking soda", "amount": 1, "unit": "tsp"},
        {"name": "salt", "amount": 1, "unit": "tsp"},
        {"name": "chocolate chips", "amount": 2, "unit": "cups"}
    ],
    "instructions": [
        "Preheat oven to 375°F (190°C)",
        "Cream butter and sugars until fluffy",
        "Beat in eggs and vanilla",
        "Mix in flour, baking soda, and salt",
        "Fold in chocolate chips",
        "Drop rounded tablespoons onto baking sheets",
        "Bake 9-11 minutes until golden brown"
    ],
    "prep_time_minutes": 15,
    "cook_time_minutes": 11,
    "servings": 48
}""",
    prompt_tokens=245,
    completion_tokens=312,
)


# Ingredient parsing response
INGREDIENT_PARSING_RESPONSE: dict[str, Any] = create_ollama_response(
    content="""{
    "original": "2 1/2 cups all-purpose flour, sifted",
    "name": "all-purpose flour",
    "amount": 2.5,
    "unit": "cups",
    "preparation": "sifted",
    "optional": false
}""",
    prompt_tokens=45,
    completion_tokens=78,
)


# Simple text response
SIMPLE_TEXT_RESPONSE: dict[str, Any] = create_ollama_response(
    content="Hello, world!",
    prompt_tokens=5,
    completion_tokens=3,
)


# Error simulation responses
MALFORMED_JSON_RESPONSE: dict[str, Any] = create_ollama_response(
    content="{ invalid json here",
)


def get_recorded_response(name: str) -> dict[str, Any]:
    """Get a recorded response by name."""
    responses = {
        "recipe_extraction": RECIPE_EXTRACTION_RESPONSE,
        "ingredient_parsing": INGREDIENT_PARSING_RESPONSE,
        "simple_text": SIMPLE_TEXT_RESPONSE,
        "malformed_json": MALFORMED_JSON_RESPONSE,
    }
    if name not in responses:
        msg = f"Unknown response: {name}. Available: {list(responses.keys())}"
        raise KeyError(msg)
    return responses[name]
