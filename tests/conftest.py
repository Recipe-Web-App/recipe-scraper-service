"""Shared test fixtures and configuration for the Recipe Scraper service tests.

This module provides pytest fixtures that are used across multiple test modules,
including database setup, mock services, and test client configuration.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from app.api.v1.schemas.common.ingredient import Ingredient as IngredientSchema
from app.api.v1.schemas.common.ingredient import Quantity as QuantitySchema
from app.api.v1.schemas.common.nutritional_info.fats import Fats as FatsSchema
from app.api.v1.schemas.common.nutritional_info.fibers import Fibers as FibersSchema
from app.api.v1.schemas.common.nutritional_info.ingredient_classification import (
    IngredientClassification as IngredientClassificationSchema,
)
from app.api.v1.schemas.common.nutritional_info.macro_nutrients import (
    MacroNutrients as MacroNutrientsSchema,
)
from app.api.v1.schemas.common.nutritional_info.minerals import (
    Minerals as MineralsSchema,
)
from app.api.v1.schemas.common.nutritional_info.sugars import Sugars as SugarsSchema
from app.api.v1.schemas.common.nutritional_info.vitams import Vitamins as VitaminsSchema
from app.api.v1.schemas.common.pagination_params import (
    PaginationParams as PaginationParamsSchema,
)
from app.api.v1.schemas.common.recipe import Recipe as RecipeSchema
from app.api.v1.schemas.common.web_recipe import WebRecipe as WebRecipeSchema
from app.api.v1.schemas.request.create_recipe_request import (
    CreateRecipeRequest as CreateRecipeRequestSchema,
)
from app.api.v1.schemas.response.create_recipe_response import (
    CreateRecipeResponse as CreateRecipeResponseSchema,
)
from app.api.v1.schemas.response.ingredient_nutritional_info_response import (
    IngredientNutritionalInfoResponse as IngredientNutritionalInfoResponseSchema,
)
from app.api.v1.schemas.response.pairing_suggestions_response import (
    PairingSuggestionsResponse as PairingSuggestionsResponseSchema,
)
from app.api.v1.schemas.response.recipe_nutritional_info_response import (
    RecipeNutritionalInfoResponse as RecipeNutritionalInfoResponseSchema,
)
from app.api.v1.schemas.response.recommended_recipes_response import (
    PopularRecipesResponse as PopularRecipesResponseSchema,
)
from app.api.v1.schemas.response.recommended_substitutions_response import (
    ConversionRatio as ConversionRatioSchema,
)
from app.api.v1.schemas.response.recommended_substitutions_response import (
    IngredientSubstitution as IngredientSubstitutionSchema,
)
from app.api.v1.schemas.response.recommended_substitutions_response import (
    RecommendedSubstitutionsResponse as RecommendedSubstitutionsResponseSchema,
)
from app.db.models.ingredient_models import Ingredient as IngredientModel
from app.db.models.recipe_models import Recipe as RecipeModel
from app.db.models.recipe_models import RecipeIngredient as RecipeIngredientModel
from app.db.models.recipe_models import RecipeReview as RecipeReviewModel
from app.db.models.recipe_models import RecipeStep as RecipeStepModel
from app.db.models.recipe_models import RecipeTagJunction as RecipeTagJunctionModel
from app.enums.allergen_enum import AllergenEnum
from app.enums.difficulty_level_enum import DifficultyLevelEnum
from app.enums.food_group_enum import FoodGroupEnum
from app.enums.ingredient_unit_enum import IngredientUnitEnum
from app.services.admin_service import AdminService
from app.services.nutritional_info_service import NutritionalInfoService
from app.services.recipe_scraper_service import RecipeScraperService
from app.services.recommendations_service import RecommendationsService


###################################
# Mocked Nutritional Info Schemas #
###################################
@pytest.fixture
def mock_ingredient_nutritional_info_schema_list() -> (
    list[IngredientNutritionalInfoResponseSchema]
):
    """Fixture for a list of fully mocked IngredientNutritionalInfoResponse objects."""
    return [
        IngredientNutritionalInfoResponseSchema(
            quantity=QuantitySchema(
                amount=Decimal(100),
                measurement=IngredientUnitEnum.G,
            ),
            classification=IngredientClassificationSchema(
                allergies=[AllergenEnum.GLUTEN, AllergenEnum.PEANUTS],
                food_groups=[FoodGroupEnum.VEGETABLES, FoodGroupEnum.FRUITS],
                nutriscore_score=85,
                nutriscore_grade="A",
                product_name="Mock Ingredient Product Name 1",
                brands="Mock Brand",
                categories="Mock Category 1",
            ),
            macro_nutrients=MacroNutrientsSchema(
                calories=180,
                carbs_g=Decimal("397.7"),
                cholesterol_mg=Decimal(100),
                protein_g=Decimal("98.8"),
                sugars=SugarsSchema(
                    sugar_g=Decimal("264.4"),
                    added_sugars_g=Decimal("52.2"),
                ),
                fats=FatsSchema(
                    fat_g=Decimal("29.9"),
                    saturated_fat_g=Decimal("7.7"),
                    monounsaturated_fat_g=Decimal("9.9"),
                    polyunsaturated_fat_g=Decimal("18.8"),
                    omega_3_fat_g=Decimal("2.21"),
                    omega_6_fat_g=Decimal("7.77"),
                    omega_9_fat_g=Decimal("2.99"),
                    trans_fat_g=Decimal("0.33"),
                ),
                fibers=FibersSchema(
                    fiber_g=Decimal("122.2"),
                    soluble_fiber_g=Decimal("44.4"),
                    insoluble_fiber_g=Decimal("88.8"),
                ),
            ),
            vitamins=VitaminsSchema(
                vitamin_a_mg=Decimal("9.93"),
                vitamin_b6_mg=Decimal("8.81"),
                vitamin_b12_mg=Decimal("11.1"),
                vitamin_c_mg=Decimal("1379.9"),
                vitamin_d_mg=Decimal("22.2"),
                vitamin_e_mg=Decimal("59.9"),
                vitamin_k_mg=Decimal("0.889"),
            ),
            minerals=MineralsSchema(
                calcium_mg=Decimal(1000),
                iron_mg=Decimal("27.77"),
                magnesium_mg=Decimal(1100),
                potassium_mg=Decimal(23700),
                sodium_mg=Decimal(500),
                zinc_mg=Decimal("17.77"),
            ),
        ),
        IngredientNutritionalInfoResponseSchema(
            quantity=QuantitySchema(
                amount=Decimal(30),
                measurement=IngredientUnitEnum.LB,
            ),
            classification=IngredientClassificationSchema(
                allergies=[AllergenEnum.SHELLFISH],
                food_groups=[FoodGroupEnum.SEAFOOD],
                nutriscore_score=-1,
                nutriscore_grade="B",
                product_name="Mock Ingredient Product Name 2",
                brands="Mock Brand 2",
                categories="Mock Category 2",
            ),
            macro_nutrients=MacroNutrientsSchema(
                calories=420,
                carbs_g=Decimal("138.8"),
                cholesterol_mg=Decimal(1200),
                protein_g=Decimal("276.6"),
                sugars=SugarsSchema(
                    sugar_g=Decimal("57.7"),
                    added_sugars_g=Decimal("23.3"),
                ),
                fats=FatsSchema(
                    fat_g=Decimal("307.7"),
                    saturated_fat_g=Decimal("168.8"),
                    monounsaturated_fat_g=Decimal("129.9"),
                    polyunsaturated_fat_g=Decimal("39.9"),
                    omega_3_fat_g=Decimal("2.99"),
                    omega_6_fat_g=Decimal("11.19"),
                    omega_9_fat_g=Decimal("59.9"),
                    trans_fat_g=Decimal("5.99"),
                ),
                fibers=FibersSchema(
                    fiber_g=Decimal("22.2"),
                    soluble_fiber_g=Decimal("11.1"),
                    insoluble_fiber_g=Decimal("11.1"),
                ),
            ),
            vitamins=VitaminsSchema(
                vitamin_a_mg=Decimal("27.55"),
                vitamin_b6_mg=Decimal("5.99"),
                vitamin_b12_mg=Decimal("29.99"),
                vitamin_c_mg=Decimal("12.2"),
                vitamin_d_mg=Decimal("17.7"),
                vitamin_e_mg=Decimal("23.3"),
                vitamin_k_mg=Decimal("0.119"),
            ),
            minerals=MineralsSchema(
                calcium_mg=Decimal(8000),
                iron_mg=Decimal("12.99"),
                magnesium_mg=Decimal(800),
                potassium_mg=Decimal(2800),
                sodium_mg=Decimal(7400),
                zinc_mg=Decimal("41.99"),
            ),
        ),
        IngredientNutritionalInfoResponseSchema(
            quantity=QuantitySchema(
                amount=Decimal(5),
                measurement=IngredientUnitEnum.TBSP,
            ),
            classification=IngredientClassificationSchema(
                allergies=[],
                food_groups=[FoodGroupEnum.POULTRY],
                nutriscore_score=2,
                nutriscore_grade="A",
                product_name="Mock Ingredient Product Name 3",
                brands="Mock Brand 3",
                categories="Mock Category 3",
            ),
            macro_nutrients=MacroNutrientsSchema(
                calories=100,
                carbs_g=Decimal("29.9"),
                cholesterol_mg=Decimal(10),
                protein_g=Decimal("19.9"),
                sugars=SugarsSchema(
                    sugar_g=Decimal("7.7"),
                    added_sugars_g=Decimal("2.2"),
                ),
                fats=FatsSchema(
                    fat_g=Decimal("2.3"),
                    saturated_fat_g=Decimal("1.4"),
                    monounsaturated_fat_g=Decimal("1.4"),
                    polyunsaturated_fat_g=Decimal("1.4"),
                    omega_3_fat_g=Decimal("0.222"),
                    omega_6_fat_g=Decimal("0.233"),
                    omega_9_fat_g=Decimal("0.255"),
                    trans_fat_g=Decimal("0.11"),
                ),
                fibers=FibersSchema(
                    fiber_g=Decimal("7.7"),
                    soluble_fiber_g=Decimal("2.3"),
                    insoluble_fiber_g=Decimal("4.7"),
                ),
            ),
            vitamins=VitaminsSchema(
                vitamin_a_mg=Decimal("2.33"),
                vitamin_b6_mg=Decimal("2.11"),
                vitamin_b12_mg=Decimal("1.1"),
                vitamin_c_mg=Decimal("28.8"),
                vitamin_d_mg=Decimal("2.2"),
                vitamin_e_mg=Decimal("2.11"),
                vitamin_k_mg=Decimal("0.114"),
            ),
            minerals=MineralsSchema(
                calcium_mg=Decimal(200),
                iron_mg=Decimal("2.33"),
                magnesium_mg=Decimal(100),
                potassium_mg=Decimal(1500),
                sodium_mg=Decimal(20),
                zinc_mg=Decimal("2.11"),
            ),
        ),
    ]


@pytest.fixture
def mock_ingredient_nutritional_info_response_schema(
    mock_ingredient_nutritional_info_schema_list: list[
        IngredientNutritionalInfoResponseSchema
    ],
) -> IngredientNutritionalInfoResponseSchema:
    """Fixture for a mocked IngredientNutritionalInfoResponse."""
    return mock_ingredient_nutritional_info_schema_list[0]


@pytest.fixture
def mock_recipe_nutritional_info_response_schema(
    mock_ingredient_nutritional_info_schema_list: list[
        IngredientNutritionalInfoResponseSchema
    ],
) -> RecipeNutritionalInfoResponseSchema:
    """Fixture for a mocked RecipeNutritionalInfoResponse including all ingredients."""
    mock_ingredient_nutritional_info_dict = {}
    for i in range(len(mock_ingredient_nutritional_info_schema_list)):
        mock_ingredient_nutritional_info_dict[i] = (
            mock_ingredient_nutritional_info_schema_list[i]
        )
    return RecipeNutritionalInfoResponseSchema(
        ingredients=mock_ingredient_nutritional_info_dict,
    )


@pytest.fixture
def mock_recipe_nutritional_info_response_schema_with_missing_ingredients(
    mock_recipe_nutritional_info_response_schema: RecipeNutritionalInfoResponseSchema,
) -> RecipeNutritionalInfoResponseSchema:
    """Fixture for a mocked RecipeNutritionalInfoResponse with missing ingredients."""
    ingredients = mock_recipe_nutritional_info_response_schema.ingredients
    ingredients_len = 0 if ingredients is None else len(ingredients)
    return RecipeNutritionalInfoResponseSchema(
        missing_ingredients=[
            ingredients_len,
            ingredients_len + 1,
        ],
        ingredients=ingredients,
    )


#################################
# Mocked Recipe Scraper Schemas #
#################################


@pytest.fixture
def mock_recipe_schema(
    mock_create_recipe_request_schema: CreateRecipeRequestSchema,
    mock_datetime: datetime,
) -> RecipeSchema:
    """Fixture for a mocked Recipe object."""
    return RecipeSchema(
        recipe_id=1,
        title="Mock Recipe",
        description="This is a mock recipe for testing purposes.",
        origin_url=mock_create_recipe_request_schema.recipe_url,
        servings=4,
        preparation_time=15,
        cooking_time=30,
        difficulty=DifficultyLevelEnum.EASY,
        ingredients=[
            IngredientSchema(
                ingredient_id=1,
                name="Mock Ingredient Name 1",
                quantity=QuantitySchema(
                    amount=Decimal(100),
                    measurement=IngredientUnitEnum.G,
                ),
            ),
            IngredientSchema(
                ingredient_id=2,
                name="Mock Ingredient Name 2",
                quantity=QuantitySchema(
                    amount=Decimal(30),
                    measurement=IngredientUnitEnum.LB,
                ),
            ),
            IngredientSchema(
                ingredient_id=3,
                name="Mock Ingredient Name 3",
                quantity=QuantitySchema(
                    amount=Decimal(5),
                    measurement=IngredientUnitEnum.TBSP,
                ),
            ),
        ],
        steps=[
            RecipeSchema.RecipeStep(
                step_number=1,
                instruction="Mock ingredient instruction 1.",
                optional=False,
                timer_seconds=60,
                created_at=mock_datetime,
            ),
            RecipeSchema.RecipeStep(
                step_number=2,
                instruction="Mock ingredient instruction 2.",
                optional=True,
                timer_seconds=None,
                created_at=mock_datetime,
            ),
            RecipeSchema.RecipeStep(
                step_number=3,
                instruction="Mock ingredient instruction 3.",
                optional=False,
                timer_seconds=120,
                created_at=mock_datetime,
            ),
        ],
    )


@pytest.fixture
def mock_create_recipe_request_schema() -> CreateRecipeRequestSchema:
    """Fixture for a mocked CreateRecipeRequest object."""
    return CreateRecipeRequestSchema(recipe_url="http://example.com/mock-recipe")


@pytest.fixture
def mock_create_recipe_response_schema(
    mock_recipe_schema: RecipeSchema,
) -> CreateRecipeResponseSchema:
    """Fixture for a mocked CreateRecipeResponse object."""
    return CreateRecipeResponseSchema(recipe=mock_recipe_schema)


@pytest.fixture
def mock_web_recipe_schema_list() -> list[WebRecipeSchema]:
    """Fixture for a list of mocked WebRecipe objects."""
    return [
        WebRecipeSchema(
            recipe_name="Popular Recipe 1",
            url="http://mock-url.com/popular-recipe-1",
        ),
        WebRecipeSchema(
            recipe_name="Popular Recipe 2",
            url="http://mock-url.com/popular-recipe-2",
        ),
        WebRecipeSchema(
            recipe_name="Popular Recipe 3",
            url="http://mock-url.com/popular-recipe-3",
        ),
        WebRecipeSchema(
            recipe_name="Popular Recipe 4",
            url="http://mock-url.com/popular-recipe-4",
        ),
        WebRecipeSchema(
            recipe_name="Popular Recipe 5",
            url="http://mock-url.com/popular-recipe-5",
        ),
    ]


@pytest.fixture
def mock_popular_recipes_response_schema(
    mock_web_recipe_schema_list: list[WebRecipeSchema],
) -> PopularRecipesResponseSchema:
    """Fixture for a mocked PopularRecipesResponse object."""
    return PopularRecipesResponseSchema(
        recipes=mock_web_recipe_schema_list,
        limit=50,
        offset=0,
        count=len(mock_web_recipe_schema_list),
    )


##########################################
# Mocked Recommendations Service Schemas #
##########################################


@pytest.fixture
def mock_ingredient_substitution_schema_list() -> list[IngredientSubstitutionSchema]:
    """Fixture for a list of mocked IngredientSchemaSubstitution objects."""
    return [
        IngredientSubstitutionSchema(
            ingredient="Mock Substitute 1",
            quantity=QuantitySchema(
                amount=Decimal(100),
                measurement=IngredientUnitEnum.G,
            ),
            conversion_ratio=ConversionRatioSchema(
                ratio=1.0,
                measurement=IngredientUnitEnum.G,
            ),
        ),
        IngredientSubstitutionSchema(
            ingredient="Mock Substitute 2",
            quantity=QuantitySchema(
                amount=Decimal(50),
                measurement=IngredientUnitEnum.G,
            ),
            conversion_ratio=ConversionRatioSchema(
                ratio=0.5,
                measurement=IngredientUnitEnum.G,
            ),
        ),
        IngredientSubstitutionSchema(
            ingredient="Mock Substitute 3",
            quantity=QuantitySchema(
                amount=Decimal(75),
                measurement=IngredientUnitEnum.G,
            ),
            conversion_ratio=ConversionRatioSchema(
                ratio=0.75,
                measurement=IngredientUnitEnum.G,
            ),
        ),
    ]


@pytest.fixture
def mock_recommended_substitutions_response_schema(
    mock_ingredient_substitution_schema_list: list[IngredientSubstitutionSchema],
) -> RecommendedSubstitutionsResponseSchema:
    """Fixture for a mocked RecommendedSubstitutionsResponse object."""
    return RecommendedSubstitutionsResponseSchema(
        ingredient=IngredientSchema(
            ingredient_id=1,
            name="Mock Ingredient Name",
            quantity=QuantitySchema(
                amount=Decimal(100),
                measurement=IngredientUnitEnum.G,
            ),
        ),
        recommended_substitutions=mock_ingredient_substitution_schema_list,
        limit=50,
        offset=0,
        count=len(mock_ingredient_substitution_schema_list),
    )


@pytest.fixture
def mock_pairing_suggestions_response_schema(
    mock_web_recipe_schema_list: list[WebRecipeSchema],
) -> PairingSuggestionsResponseSchema:
    """Fixture for a mocked PairingSuggestionsResponse object."""
    return PairingSuggestionsResponseSchema(
        recipe_id=1,
        pairing_suggestions=mock_web_recipe_schema_list,
        limit=50,
        offset=0,
        count=len(mock_web_recipe_schema_list),
    )


#########################
# Mocked Common Schemas #
#########################
@pytest.fixture
def mock_quantity_schema() -> QuantitySchema:
    """Fixture for a mocked QuantitySchema object."""
    return QuantitySchema(amount=Decimal(100), measurement=IngredientUnitEnum.G)


@pytest.fixture
def mock_pagination_params_schema() -> PaginationParamsSchema:
    """Fixture for a mocked PaginationParams object."""
    return PaginationParamsSchema(limit=2, offset=2, count_only=False)


@pytest.fixture
def mock_pagination_params_schema_count_only(
    default_pagination_params_schema: PaginationParamsSchema,
) -> PaginationParamsSchema:
    """Fixture for a mocked PaginationParams object configured for count only."""
    default_pagination_params_schema.count_only = True
    return default_pagination_params_schema


@pytest.fixture
def mock_pagination_params_schema_invalid_range() -> PaginationParamsSchema:
    """Fixture for a mocked PaginationParams object with invalid limit & offset vals."""
    return PaginationParamsSchema(limit=5, offset=10)


@pytest.fixture
def default_pagination_params_schema() -> PaginationParamsSchema:
    """Fixture for a PaginationParams object with the default runtime values."""
    return PaginationParamsSchema(limit=50, offset=0, count_only=False)


#########################
# Mocked Recipes Models #
#########################


@pytest.fixture
def mock_ingredient_list(mock_datetime: datetime) -> list[IngredientModel]:
    """Fixture for a list of mocked Ingredient objects."""
    return [
        IngredientModel(
            ingredient_id=1,
            name="Mock Ingredient 1",
            description="Description for Mock Ingredient 1",
            is_optional=False,
            created_at=mock_datetime,
            updated_at=mock_datetime,
        ),
        IngredientModel(
            ingredient_id=2,
            name="Mock Ingredient 2",
            description="Description for Mock Ingredient 2",
            is_optional=True,
            created_at=mock_datetime,
            updated_at=mock_datetime,
        ),
        IngredientModel(
            ingredient_id=3,
            name="Mock Ingredient 3",
            description="Description for Mock Ingredient 3",
            is_optional=False,
            created_at=mock_datetime,
            updated_at=mock_datetime,
        ),
    ]


@pytest.fixture
def mock_recipe_ingredient_list(
    mock_ingredient_list: list[IngredientModel],
) -> list[RecipeIngredientModel]:
    """Fixture for a list of mocked RecipeIngredient objects."""
    return [
        RecipeIngredientModel(
            recipe_id=1,
            ingredient_id=mock_ingredient_list[0].ingredient_id,
            quantity=Decimal(100),
            unit=IngredientUnitEnum.G,
            is_optional=False,
        ),
        RecipeIngredientModel(
            recipe_id=1,
            ingredient_id=mock_ingredient_list[1].ingredient_id,
            quantity=Decimal(30),
            unit=IngredientUnitEnum.LB,
            is_optional=True,
        ),
        RecipeIngredientModel(
            recipe_id=1,
            ingredient_id=mock_ingredient_list[2].ingredient_id,
            quantity=Decimal(5),
            unit=IngredientUnitEnum.TBSP,
            is_optional=False,
        ),
    ]


@pytest.fixture
def mock_recipe_step_list(mock_datetime: datetime) -> list[RecipeStepModel]:
    """Fixture for a list of mocked RecipeStep objects."""
    return [
        RecipeStepModel(
            step_id=1,
            recipe_id=1,
            step_number=1,
            instruction="This is the first step of the mock recipe.",
            optional=False,
            timer_seconds=60,
            created_at=mock_datetime,
        ),
        RecipeStepModel(
            step_id=2,
            recipe_id=1,
            step_number=2,
            instruction="This is the second step of the mock recipe.",
            optional=True,
            timer_seconds=None,
            created_at=mock_datetime,
        ),
        RecipeStepModel(
            step_id=3,
            recipe_id=1,
            step_number=3,
            instruction="This is the third step of the mock recipe.",
            optional=False,
            timer_seconds=120,
            created_at=mock_datetime,
        ),
    ]


@pytest.fixture
def mock_recipe_tag_list() -> list[RecipeTagJunctionModel]:
    """Fixture for a list of mocked RecipeTagJunction objects."""
    return [
        RecipeTagJunctionModel(
            recipe_id=1,
            tag_id=1,
        ),
        RecipeTagJunctionModel(
            recipe_id=1,
            tag_id=2,
        ),
        RecipeTagJunctionModel(
            recipe_id=1,
            tag_id=3,
        ),
    ]


@pytest.fixture
def mock_recipe_review_list(
    mock_user_id: UUID,
    mock_datetime: datetime,
) -> list[RecipeReviewModel]:
    """Fixture for a list of mocked RecipeReview objects."""
    return [
        RecipeReviewModel(
            review_id=1,
            recipe_id=1,
            user_id=mock_user_id,
            rating=4.5,
            comment="Mock recipe review comment 1.",
            created_at=mock_datetime,
        ),
        RecipeReviewModel(
            review_id=2,
            recipe_id=1,
            user_id=mock_user_id,
            rating=3.0,
            comment="Mock recipe review comment 2.",
            created_at=mock_datetime,
        ),
    ]


@pytest.fixture
def mock_recipe_model(  # noqa: PLR0913
    mock_user_id: UUID,
    mock_recipe_ingredient_list: list[RecipeIngredientModel],
    mock_recipe_step_list: list[RecipeStepModel],
    mock_recipe_tag_list: list[RecipeTagJunctionModel],
    mock_recipe_review_list: list[RecipeReviewModel],
    mock_datetime: datetime,
) -> RecipeModel:
    """Fixture for a mocked Recipe object."""
    return RecipeModel(
        recipe_id=1,
        user_id=mock_user_id,
        title="Mock Recipe Title",
        description="Mock recipe description.",
        origin_url="https://mock-url.com/mock-recipe",
        servings=4.0,
        preparation_time=15,
        cooking_time=30,
        difficulty=DifficultyLevelEnum.EASY,
        created_at=mock_datetime,
        updated_at=mock_datetime,
        ingredients=mock_recipe_ingredient_list,
        steps=mock_recipe_step_list,
        tags=mock_recipe_tag_list,
        reviews=mock_recipe_review_list,
    )


#####################
# Misc. Mocked Data #
#####################


@pytest.fixture
def mock_user_id() -> UUID:
    """Fixture for a mocked user ID."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def mock_datetime() -> datetime:
    """Fixture for a mocked datetime object."""
    return datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)


###################
# Mocked Services #
###################


@pytest.fixture
def mock_admin_service() -> Mock:
    """Create a mock AdminService for testing.

    Returns:     Mock: Mocked AdminService instance
    """
    mock_service = Mock(spec=AdminService)
    mock_service.clear_cache = AsyncMock(return_value=None)
    return mock_service


@pytest.fixture
def mock_cache_manager() -> Mock:
    """Create a mock EnhancedCacheManager for testing.

    Returns:     Mock: Mocked EnhancedCacheManager instance
    """
    mock_cache = Mock()
    mock_cache.clear_all = AsyncMock(return_value=None)
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock(return_value=None)
    mock_cache.delete = AsyncMock(return_value=None)
    mock_cache.is_valid = AsyncMock(return_value=False)
    return mock_cache


@pytest.fixture
def mock_nutritional_info_service(
    mock_recipe_nutritional_info_response_schema: RecipeNutritionalInfoResponseSchema,
    mock_ingredient_nutritional_info_response_schema: (
        IngredientNutritionalInfoResponseSchema
    ),
) -> Mock:
    """Fixture for a mocked NutritionalInfoService with a preset return value."""
    mock = Mock(spec=NutritionalInfoService)
    mock.get_recipe_nutritional_info.return_value = (
        mock_recipe_nutritional_info_response_schema
    )
    mock.get_ingredient_nutritional_info.return_value = (
        mock_ingredient_nutritional_info_response_schema
    )
    return mock


@pytest.fixture
def mock_recipe_scraper_service(
    mock_create_recipe_response_schema: CreateRecipeResponseSchema,
    mock_popular_recipes_response_schema: PopularRecipesResponseSchema,
) -> Mock:
    """Fixture for a mocked RecipeScraperService with preset return values."""
    mock = Mock(spec=RecipeScraperService)
    mock.create_recipe.return_value = mock_create_recipe_response_schema
    mock.get_popular_recipes = AsyncMock(
        return_value=mock_popular_recipes_response_schema
    )
    return mock


@pytest.fixture
def mock_recommendations_service(
    mock_recommended_substitutions_response_schema: (
        RecommendedSubstitutionsResponseSchema
    ),
    mock_pairing_suggestions_response_schema: PairingSuggestionsResponseSchema,
) -> Mock:
    """Fixture for a mocked RecommendationsService with preset return values."""
    mock = Mock(spec=RecommendationsService)
    mock.get_recommended_substitutions.return_value = (
        mock_recommended_substitutions_response_schema
    )
    mock.get_pairing_suggestions = AsyncMock(
        return_value=mock_pairing_suggestions_response_schema
    )
    return mock


####################
# Helper Utilities #
####################
class IsType:
    """Utility class for type checking in assertions."""

    def __init__(self, expected_type: type) -> None:
        """Initialize IsType with the expected type for type checking."""
        self.expected_type = expected_type

    def __eq__(self, other: object) -> bool:
        """Check if the other object is an instance of the expected type."""
        return isinstance(other, self.expected_type)

    def __hash__(self) -> int:
        """Return the hash based on the expected type."""
        return hash(self.expected_type)

    def __repr__(self) -> str:
        """Return the string representation of the IsType instance."""
        return f"IsType({self.expected_type.__name__})"
