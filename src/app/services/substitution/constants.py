"""Constants for substitution service configuration.

Contains:
- Cache configuration for substitution data
- Generation limits for LLM output
"""

from __future__ import annotations

from typing import Final


# =============================================================================
# Cache Configuration
# =============================================================================

SUBSTITUTION_CACHE_KEY_PREFIX: Final[str] = "substitution"
SUBSTITUTION_CACHE_TTL_SECONDS: Final[int] = 7 * 24 * 60 * 60  # 7 days


# =============================================================================
# LLM Generation Limits
# =============================================================================

MIN_SUBSTITUTIONS: Final[int] = 5
MAX_SUBSTITUTIONS: Final[int] = 10
