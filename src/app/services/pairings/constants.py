"""Constants for pairings service configuration.

Contains:
- Cache configuration for pairing data
- Generation limits for LLM output
"""

from __future__ import annotations

from typing import Final


# =============================================================================
# Cache Configuration
# =============================================================================

PAIRINGS_CACHE_KEY_PREFIX: Final[str] = "pairing"
PAIRINGS_CACHE_TTL_SECONDS: Final[int] = 24 * 60 * 60  # 24 hours


# =============================================================================
# LLM Generation Limits
# =============================================================================

MIN_PAIRINGS: Final[int] = 5
MAX_PAIRINGS: Final[int] = 15
