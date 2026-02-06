"""Parsing exceptions.

This module defines exceptions specific to parsing operations,
particularly ingredient parsing via LLM.
"""

from __future__ import annotations


class ParsingError(Exception):
    """Base exception for parsing errors."""


class IngredientParsingError(ParsingError):
    """Raised when ingredient parsing fails.

    This can occur when the LLM fails to parse ingredient strings
    into structured data.
    """


class IngredientParsingTimeoutError(IngredientParsingError):
    """Raised when ingredient parsing times out."""


class IngredientParsingValidationError(IngredientParsingError):
    """Raised when parsed ingredients fail validation.

    The LLM returned a response, but it doesn't conform to the
    expected ingredient schema.
    """
