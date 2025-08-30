"""Exceptions package initializer.

Includes custom exceptions and their handlers for centralized error management.
"""

from .custom_exceptions import DatabaseUnavailableError

__all__ = ["DatabaseUnavailableError"]
