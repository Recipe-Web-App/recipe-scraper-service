"""Pydantic schemas for request/response validation.

This module exports all schema classes for the Recipe Scraper API.
"""

# Auth schemas (existing)
from app.schemas.auth import (
    PasswordChange,
    PasswordReset,
    PasswordResetConfirm,
    RefreshTokenRequest,
    TokenInfo,
    TokenRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)

# Base classes
from app.schemas.base import (
    APIRequest,
    APIResponse,
    DownstreamRequest,
    DownstreamResponse,
)

# Enums
from app.schemas.enums import (
    Allergen,
    Difficulty,
    FoodGroup,
    HealthStatus,
    IngredientUnit,
    NutriscoreGrade,
    ReadinessStatus,
)

# Health schemas
from app.schemas.health import (
    DatabaseMonitoring,
    ExternalApisHealth,
    HealthCheckItem,
    HealthCheckResponse,
    HealthChecks,
)

# Ingredient schemas
from app.schemas.ingredient import (
    Ingredient,
    Quantity,
    WebRecipe,
)

# Nutrition schemas
from app.schemas.nutrition import (
    Fats,
    Fibers,
    IngredientClassification,
    IngredientNutritionalInfoResponse,
    MacroNutrients,
    Minerals,
    RecipeNutritionalInfoResponse,
    Sugars,
    Vitamins,
)

# Recipe schemas
from app.schemas.recipe import (
    CreateRecipeRequest,
    CreateRecipeResponse,
    PopularRecipesResponse,
    Recipe,
    RecipeStep,
)

# Recommendation schemas
from app.schemas.recommendations import (
    ConversionRatio,
    IngredientSubstitution,
    PairingSuggestionsResponse,
    RecommendedSubstitutionsResponse,
)

# Root schemas
from app.schemas.root import RootResponse

# Shopping schemas
from app.schemas.shopping import (
    IngredientShoppingInfoResponse,
    RecipeShoppingInfoResponse,
)


__all__ = [
    "APIRequest",
    "APIResponse",
    "Allergen",
    "ConversionRatio",
    "CreateRecipeRequest",
    "CreateRecipeResponse",
    "DatabaseMonitoring",
    "Difficulty",
    "DownstreamRequest",
    "DownstreamResponse",
    "ExternalApisHealth",
    "Fats",
    "Fibers",
    "FoodGroup",
    "HealthCheckItem",
    "HealthCheckResponse",
    "HealthChecks",
    "HealthStatus",
    "Ingredient",
    "IngredientClassification",
    "IngredientNutritionalInfoResponse",
    "IngredientShoppingInfoResponse",
    "IngredientSubstitution",
    "IngredientUnit",
    "MacroNutrients",
    "Minerals",
    "NutriscoreGrade",
    "PairingSuggestionsResponse",
    "PasswordChange",
    "PasswordReset",
    "PasswordResetConfirm",
    "PopularRecipesResponse",
    "Quantity",
    "ReadinessStatus",
    "Recipe",
    "RecipeNutritionalInfoResponse",
    "RecipeShoppingInfoResponse",
    "RecipeStep",
    "RecommendedSubstitutionsResponse",
    "RefreshTokenRequest",
    "RootResponse",
    "Sugars",
    "TokenInfo",
    "TokenRequest",
    "TokenResponse",
    "UserCreate",
    "UserResponse",
    "Vitamins",
    "WebRecipe",
]
