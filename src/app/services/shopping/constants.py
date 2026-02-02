"""Constants for shopping service configuration.

Contains:
- Cache configuration for pricing data
- Confidence scores for different pricing tiers
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final


# =============================================================================
# Cache Configuration
# =============================================================================

SHOPPING_CACHE_KEY_PREFIX: Final[str] = "shopping"
SHOPPING_CACHE_TTL_SECONDS: Final[int] = 24 * 60 * 60  # 24 hours


# =============================================================================
# Pricing Tier Confidence Scores
# =============================================================================
# Higher confidence for direct ingredient pricing, lower for food group averages

TIER_1_CONFIDENCE: Final[Decimal] = Decimal("0.95")  # Direct ingredient pricing
TIER_2_CONFIDENCE: Final[Decimal] = Decimal("0.60")  # Food group average
