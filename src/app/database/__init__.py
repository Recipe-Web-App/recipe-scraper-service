"""PostgreSQL database layer.

This module provides:
- Connection pool management
- Repository classes for data access
- Health check utilities
"""

from app.database.connection import (
    check_database_health,
    close_database_pool,
    get_database_pool,
    init_database_pool,
)
from app.database.repositories.nutrition import (
    MacronutrientsData,
    MineralsData,
    NutritionData,
    NutritionRepository,
    VitaminsData,
)


__all__ = [
    "MacronutrientsData",
    "MineralsData",
    "NutritionData",
    "NutritionRepository",
    "VitaminsData",
    "check_database_health",
    "close_database_pool",
    "get_database_pool",
    "init_database_pool",
]
