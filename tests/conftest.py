"""Shared test fixtures and configuration for the Recipe Scraper service tests.

This module provides pytest fixtures that are used across multiple test modules,
including database setup, mock services, and test client configuration.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import Mock
from uuid import UUID

import pytest

from app.api.v1.schemas.common.ingredient import Ingredient, Quantity
from app.api.v1.schemas.common.nutritional_info.fats import Fats
from app.api.v1.schemas.common.nutritional_info.fibers import Fibers
from app.api.v1.schemas.common.nutritional_info.ingredient_classification import (
    IngredientClassification,
)
from app.api.v1.schemas.common.nutritional_info.macro_nutrients import MacroNutrients
from app.api.v1.schemas.common.nutritional_info.minerals import Minerals
from app.api.v1.schemas.common.nutritional_info.sugars import Sugars
from app.api.v1.schemas.common.nutritional_info.vitams import Vitamins
from app.api.v1.schemas.common.recipe import Recipe
from app.api.v1.schemas.common.web_recipe import WebRecipe
from app.api.v1.schemas.request.create_recipe_request import CreateRecipeRequest
from app.api.v1.schemas.response.create_recipe_response import CreateRecipeResponse
from app.api.v1.schemas.response.ingredient_nutritional_info_response import (
    IngredientNutritionalInfoResponse,
)
from app.api.v1.schemas.response.recipe_nutritional_info_response import (
    RecipeNutritionalInfoResponse,
)
from app.api.v1.schemas.response.recommended_recipes_response import (
    PopularRecipesResponse,
)
from app.enums.allergen_enum import AllergenEnum
from app.enums.difficulty_level_enum import DifficultyLevelEnum
from app.enums.food_group_enum import FoodGroupEnum
from app.enums.ingredient_unit_enum import IngredientUnitEnum
from app.services.admin_service import AdminService
from app.services.nutritional_info_service import NutritionalInfoService
from app.services.recipe_scraper_service import RecipeScraperService


###################################
# Mocked Nutritional Info Schemas #
###################################
@pytest.fixture
def mock_ingredient_nutritional_info_list() -> list[IngredientNutritionalInfoResponse]:
    """Fixture for a list of fully mocked IngredientNutritionalInfoResponse objects."""
    return [
        IngredientNutritionalInfoResponse(
            quantity=Quantity(amount=Decimal(100), measurement=IngredientUnitEnum.G),
            classification=IngredientClassification(
                allergies=[AllergenEnum.GLUTEN, AllergenEnum.PEANUTS],
                food_groups=[FoodGroupEnum.VEGETABLES, FoodGroupEnum.FRUITS],
                nutriscore_score=85,
                nutriscore_grade="A",
                product_name="Mock Ingredient 1",
                brands="Mock Brand",
                categories="Mock Category 1",
            ),
            macro_nutrients=MacroNutrients(
                calories=180,
                carbs_g=Decimal("397.7"),
                cholesterol_mg=Decimal(100),
                protein_g=Decimal("98.8"),
                sugars=Sugars(sugar_g=Decimal("264.4"), added_sugars_g=Decimal("52.2")),
                fats=Fats(
                    fat_g=Decimal("29.9"),
                    saturated_fat_g=Decimal("7.7"),
                    monounsaturated_fat_g=Decimal("9.9"),
                    polyunsaturated_fat_g=Decimal("18.8"),
                    omega_3_fat_g=Decimal("2.21"),
                    omega_6_fat_g=Decimal("7.77"),
                    omega_9_fat_g=Decimal("2.99"),
                    trans_fat_g=Decimal("0.33"),
                ),
                fibers=Fibers(
                    fiber_g=Decimal("122.2"),
                    soluble_fiber_g=Decimal("44.4"),
                    insoluble_fiber_g=Decimal("88.8"),
                ),
            ),
            vitamins=Vitamins(
                vitamin_a_mg=Decimal("9.93"),
                vitamin_b6_mg=Decimal("8.81"),
                vitamin_b12_mg=Decimal("11.1"),
                vitamin_c_mg=Decimal("1379.9"),
                vitamin_d_mg=Decimal("22.2"),
                vitamin_e_mg=Decimal("59.9"),
                vitamin_k_mg=Decimal("0.889"),
            ),
            minerals=Minerals(
                calcium_mg=Decimal(1000),
                iron_mg=Decimal("27.77"),
                magnesium_mg=Decimal(1100),
                potassium_mg=Decimal(23700),
                sodium_mg=Decimal(500),
                zinc_mg=Decimal("17.77"),
            ),
        ),
        IngredientNutritionalInfoResponse(
            quantity=Quantity(amount=Decimal(30), measurement=IngredientUnitEnum.LB),
            classification=IngredientClassification(
                allergies=[AllergenEnum.SHELLFISH],
                food_groups=[FoodGroupEnum.SEAFOOD],
                nutriscore_score=-1,
                nutriscore_grade="B",
                product_name="Mock Ingredient 2",
                brands="Mock Brand 2",
                categories="Mock Category 2",
            ),
            macro_nutrients=MacroNutrients(
                calories=420,
                carbs_g=Decimal("138.8"),
                cholesterol_mg=Decimal(1200),
                protein_g=Decimal("276.6"),
                sugars=Sugars(sugar_g=Decimal("57.7"), added_sugars_g=Decimal("23.3")),
                fats=Fats(
                    fat_g=Decimal("307.7"),
                    saturated_fat_g=Decimal("168.8"),
                    monounsaturated_fat_g=Decimal("129.9"),
                    polyunsaturated_fat_g=Decimal("39.9"),
                    omega_3_fat_g=Decimal("2.99"),
                    omega_6_fat_g=Decimal("11.19"),
                    omega_9_fat_g=Decimal("59.9"),
                    trans_fat_g=Decimal("5.99"),
                ),
                fibers=Fibers(
                    fiber_g=Decimal("22.2"),
                    soluble_fiber_g=Decimal("11.1"),
                    insoluble_fiber_g=Decimal("11.1"),
                ),
            ),
            vitamins=Vitamins(
                vitamin_a_mg=Decimal("27.55"),
                vitamin_b6_mg=Decimal("5.99"),
                vitamin_b12_mg=Decimal("29.99"),
                vitamin_c_mg=Decimal("12.2"),
                vitamin_d_mg=Decimal("17.7"),
                vitamin_e_mg=Decimal("23.3"),
                vitamin_k_mg=Decimal("0.119"),
            ),
            minerals=Minerals(
                calcium_mg=Decimal(8000),
                iron_mg=Decimal("12.99"),
                magnesium_mg=Decimal(800),
                potassium_mg=Decimal(2800),
                sodium_mg=Decimal(7400),
                zinc_mg=Decimal("41.99"),
            ),
        ),
        IngredientNutritionalInfoResponse(
            quantity=Quantity(amount=Decimal(5), measurement=IngredientUnitEnum.TBSP),
            classification=IngredientClassification(
                allergies=[],
                food_groups=[FoodGroupEnum.POULTRY],
                nutriscore_score=2,
                nutriscore_grade="A",
                product_name="Mock Ingredient 3",
                brands="Mock Brand 3",
                categories="Mock Category 3",
            ),
            macro_nutrients=MacroNutrients(
                calories=100,
                carbs_g=Decimal("29.9"),
                cholesterol_mg=Decimal(10),
                protein_g=Decimal("19.9"),
                sugars=Sugars(sugar_g=Decimal("7.7"), added_sugars_g=Decimal("2.2")),
                fats=Fats(
                    fat_g=Decimal("2.3"),
                    saturated_fat_g=Decimal("1.4"),
                    monounsaturated_fat_g=Decimal("1.4"),
                    polyunsaturated_fat_g=Decimal("1.4"),
                    omega_3_fat_g=Decimal("0.222"),
                    omega_6_fat_g=Decimal("0.233"),
                    omega_9_fat_g=Decimal("0.255"),
                    trans_fat_g=Decimal("0.11"),
                ),
                fibers=Fibers(
                    fiber_g=Decimal("7.7"),
                    soluble_fiber_g=Decimal("2.3"),
                    insoluble_fiber_g=Decimal("4.7"),
                ),
            ),
            vitamins=Vitamins(
                vitamin_a_mg=Decimal("2.33"),
                vitamin_b6_mg=Decimal("2.11"),
                vitamin_b12_mg=Decimal("1.1"),
                vitamin_c_mg=Decimal("28.8"),
                vitamin_d_mg=Decimal("2.2"),
                vitamin_e_mg=Decimal("2.11"),
                vitamin_k_mg=Decimal("0.114"),
            ),
            minerals=Minerals(
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
def mock_ingredient_nutritional_info_response(
    mock_ingredient_nutritional_info_list: list[IngredientNutritionalInfoResponse],
) -> IngredientNutritionalInfoResponse:
    """Fixture for a mocked IngredientNutritionalInfoResponse."""
    return mock_ingredient_nutritional_info_list[0]


@pytest.fixture
def mock_recipe_nutritional_info_response(
    mock_ingredient_nutritional_info_list: list[IngredientNutritionalInfoResponse],
) -> RecipeNutritionalInfoResponse:
    """Fixture for a mocked RecipeNutritionalInfoResponse including all ingredients."""
    mock_ingredient_nutritional_info_dict = {}
    for i in range(len(mock_ingredient_nutritional_info_list)):
        mock_ingredient_nutritional_info_dict[i] = (
            mock_ingredient_nutritional_info_list[i]
        )
    return RecipeNutritionalInfoResponse(
        ingredients=mock_ingredient_nutritional_info_dict,
    )


@pytest.fixture
def mock_recipe_nutritional_info_response_with_missing_ingredients(
    mock_recipe_nutritional_info_response: RecipeNutritionalInfoResponse,
) -> RecipeNutritionalInfoResponse:
    """Fixture for a mocked RecipeNutritionalInfoResponse with missing ingredients."""
    ingredients = mock_recipe_nutritional_info_response.ingredients
    ingredients_len = 0 if ingredients is None else len(ingredients)
    return RecipeNutritionalInfoResponse(
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
def mock_recipe(
    mock_create_recipe_request: CreateRecipeRequest,
    mock_datetime: datetime,
) -> Recipe:
    """Fixture for a mocked Recipe object."""
    return Recipe(
        recipe_id=1,
        title="Mock Recipe",
        description="This is a mock recipe for testing purposes.",
        origin_url=mock_create_recipe_request.recipe_url,
        servings=4,
        preparation_time=15,
        cooking_time=30,
        difficulty=DifficultyLevelEnum.EASY,
        ingredients=[
            Ingredient(
                ingredient_id=1,
                name="Mock Ingredient 1",
                quantity=Quantity(
                    amount=Decimal(100),
                    measurement=IngredientUnitEnum.G,
                ),
            ),
            Ingredient(
                ingredient_id=2,
                name="Mock Ingredient 2",
                quantity=Quantity(
                    amount=Decimal(30),
                    measurement=IngredientUnitEnum.LB,
                ),
            ),
            Ingredient(
                ingredient_id=3,
                name="Mock Ingredient 3",
                quantity=Quantity(
                    amount=Decimal(5),
                    measurement=IngredientUnitEnum.TBSP,
                ),
            ),
        ],
        steps=[
            Recipe.RecipeStep(
                step_number=1,
                instruction="This is the first step of the mock recipe.",
                optional=False,
                timer_seconds=60,
                created_at=mock_datetime,
            ),
            Recipe.RecipeStep(
                step_number=2,
                instruction="This is the second step of the mock recipe.",
                optional=True,
                timer_seconds=None,
                created_at=mock_datetime,
            ),
            Recipe.RecipeStep(
                step_number=3,
                instruction="This is the third step of the mock recipe.",
                optional=False,
                timer_seconds=120,
                created_at=mock_datetime,
            ),
        ],
    )


@pytest.fixture
def mock_create_recipe_request() -> CreateRecipeRequest:
    """Fixture for a mocked CreateRecipeRequest object."""
    return CreateRecipeRequest(recipe_url="http://example.com/mock-recipe")


@pytest.fixture
def mock_create_recipe_response(mock_recipe: Recipe) -> CreateRecipeResponse:
    """Fixture for a mocked CreateRecipeResponse object."""
    return CreateRecipeResponse(recipe=mock_recipe)


@pytest.fixture
def mock_web_recipe_list() -> list[WebRecipe]:
    """Fixture for a list of mocked WebRecipe objects."""
    return [
        WebRecipe(
            recipe_name="Popular Recipe 1",
            url="http://example.com/popular-recipe-1",
        ),
        WebRecipe(
            recipe_name="Popular Recipe 2",
            url="http://example.com/popular-recipe-2",
        ),
        WebRecipe(
            recipe_name="Popular Recipe 3",
            url="http://example.com/popular-recipe-3",
        ),
        WebRecipe(
            recipe_name="Popular Recipe 4",
            url="http://example.com/popular-recipe-4",
        ),
        WebRecipe(
            recipe_name="Popular Recipe 5",
            url="http://example.com/popular-recipe-5",
        ),
    ]


@pytest.fixture
def mock_popular_recipes_response(
    mock_web_recipe_list: list[WebRecipe],
) -> PopularRecipesResponse:
    """Fixture for a mocked PopularRecipesResponse object."""
    return PopularRecipesResponse(
        recipes=mock_web_recipe_list,
        limit=50,
        offset=0,
        count=len(mock_web_recipe_list),
    )


#########################
# Mocked Common Schemas #
#########################
@pytest.fixture
def mock_quantity() -> Quantity:
    """Fixture for a mocked Quantity object."""
    return Quantity(amount=Decimal(100), measurement=IngredientUnitEnum.G)


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

    Returns:
        Mock: Mocked AdminService instance
    """
    mock_service = Mock(spec=AdminService)
    mock_service.clear_cache.return_value = None
    return mock_service


@pytest.fixture
def mock_cache_manager() -> Mock:
    """Create a mock CacheManager for testing.

    Returns:
        Mock: Mocked CacheManager instance
    """
    mock_cache = Mock()
    mock_cache.clear_all.return_value = None
    return mock_cache


@pytest.fixture
def mock_nutritional_info_service(
    mock_recipe_nutritional_info_response: RecipeNutritionalInfoResponse,
    mock_ingredient_nutritional_info_response: IngredientNutritionalInfoResponse,
) -> Mock:
    """Fixture for a mocked NutritionalInfoService with a preset return value."""
    mock = Mock(spec=NutritionalInfoService)
    mock.get_recipe_nutritional_info.return_value = (
        mock_recipe_nutritional_info_response
    )
    mock.get_ingredient_nutritional_info.return_value = (
        mock_ingredient_nutritional_info_response
    )
    return mock


@pytest.fixture
def mock_recipe_scraper_service(
    mock_create_recipe_response: CreateRecipeResponse,
    mock_popular_recipes_response: PopularRecipesResponse,
) -> Mock:
    """Fixture for a mocked RecipeScraperService with preset return values."""
    mock = Mock(spec=RecipeScraperService)
    mock.create_recipe.return_value = mock_create_recipe_response
    mock.get_popular_recipes.return_value = mock_popular_recipes_response
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
