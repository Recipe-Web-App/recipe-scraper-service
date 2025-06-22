"""Recipe scraper service module.

Provides functionality to retrieve detailed recipe information from the internet using
recipe_scraper and beautiful_soup.

Includes logging for traceability and debugging.
"""

import re
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from uuid import UUID

from fastapi import HTTPException
from recipe_scrapers import scrape_me
from sqlalchemy.orm import Session

from app.api.v1.schemas.common.ingredient import Ingredient as IngredientSchema
from app.api.v1.schemas.common.ingredient import Quantity as QuantitySchema
from app.api.v1.schemas.common.pagination_params import PaginationParams
from app.api.v1.schemas.common.recipe import Recipe as RecipeSchema
from app.api.v1.schemas.common.web_recipe import WebRecipe
from app.api.v1.schemas.response.create_recipe_response import CreateRecipeResponse
from app.api.v1.schemas.response.pairing_suggestions_response import (
    PairingSuggestionsResponse,
)
from app.api.v1.schemas.response.recommended_recipes_response import (
    PopularRecipesResponse,
)
from app.api.v1.schemas.response.recommended_substitutions_response import (
    IngredientSubstitution,
    RecommendedSubstitutionsResponse,
)
from app.core.config.config import settings
from app.core.logging import get_logger
from app.db.models.ingredient_models.ingredient import Ingredient as IngredientModel
from app.db.models.recipe_models.recipe import Recipe
from app.db.models.recipe_models.recipe_ingredient import RecipeIngredient
from app.db.models.recipe_models.recipe_step import RecipeStep
from app.enums.ingredient_unit_enum import IngredientUnitEnum
from app.exceptions.custom_exceptions import RecipeScrapingError
from app.utils.popular_recipe_web_scraper import scrape_popular_recipes

_log = get_logger(__name__)


def _parse_ingredient_string(
    ingredient_str: str,
) -> tuple[Decimal | None, IngredientUnitEnum | None, str]:
    """Parse an ingredient string into quantity, unit, and name.

    Args:
        ingredient_str (str): The raw ingredient string.

    Returns:
        tuple[Decimal|None, IngredientUnitEnum|None, str]: (quantity, unit, name)
    """
    # Regex to match quantity (including fractions), unit, and name
    pattern = (
        r"^\s*"
        r"(?P<quantity>(\d+\s\d+/\d+)|(\d+/\d+)|(\d+\.\d+)|(\d+))?"
        r"\s*(?P<unit>\w+)?\s*(?P<name>.+)"
    )
    match = re.match(pattern, ingredient_str)
    quantity = None
    unit = None
    name = ingredient_str

    if match:
        qty_str = match.group("quantity")
        unit_str = match.group("unit")
        name = match.group("name").strip()

        # Parse quantity
        if qty_str:
            qty_str = qty_str.strip()
            try:
                if " " in qty_str and "/" in qty_str:
                    # Mixed fraction, e.g. "1 1/2"
                    whole, frac = qty_str.split(" ")
                    quantity = Decimal(whole) + Decimal(str(float(Fraction(frac))))
                elif "/" in qty_str:
                    # Simple fraction, e.g. "1/2"
                    quantity = Decimal(str(float(Fraction(qty_str))))
                else:
                    quantity = Decimal(qty_str)
            except (ValueError, ZeroDivisionError, InvalidOperation) as e:
                _log.warning("Error parsing quantity from '{}': {}", qty_str, e)
                quantity = None

        # Parse unit
        if unit_str:
            unit_str = unit_str.lower()
            try:
                unit = IngredientUnitEnum.from_string(unit_str)
            except ValueError:
                _log.error(
                    "Unsupported unit '{}' in ingredient '{}'. Defaulting to None.",
                    unit_str,
                    ingredient_str,
                )
                unit = None

    return quantity, unit, name


class RecipeScraperService:
    """Service to retrieve recipe information by scraping data from websites.

    This service provides methods to obtain detailed recipe data using recipe_scraper
    and beautiful_soup.
    """

    def create_recipe(
        self,
        url: str,
        db: Session,
        user_id: UUID,
    ) -> CreateRecipeResponse:
        """Create a recipe from the given URL using recipe_scraper and persist it.

        Args:
            url (str): The URL of the recipe to scrape.
            db (Session): The database session to add the recipe to.
            user_id (UUID): The unique identifier of the user creating the recipe.

        Returns:
            CreateRecipeResponse: The response containing the recipe data.
        """
        _log.info("Creating recipe from URL: {}", url)

        existing_recipe = (
            db.query(Recipe)
            .filter(
                Recipe.origin_url == url,
                Recipe.user_id == user_id,
            )
            .first()
        )
        if existing_recipe:
            _log.info(
                "Recipe ID {} already exists for user {} with URL '{}'.",
                existing_recipe.recipe_id,
                user_id,
                url,
            )
            raise HTTPException(
                status_code=409,
                detail={
                    "message": f"Recipe ID {existing_recipe.recipe_id} already exists.",
                },
            )

        scraper = scrape_me(url)
        data = scraper.to_json()
        _log.debug("Scraped Recipe: {}", data)

        # Parse servings as a number if possible
        servings = None
        if data.get("yields"):
            try:
                servings = float(data["yields"].split()[0])
            except (ValueError, AttributeError, IndexError) as e:
                _log.warning(
                    "Error parsing servings from yields '{}': {}",
                    data["yields"],
                    e,
                )
                servings = None

        # Create Recipe instance
        recipe = Recipe(
            user_id=user_id,
            title=data.get("title"),
            description=data.get("description"),
            origin_url=data.get("canonical_url"),
            servings=servings,
            preparation_time=data.get("prep_time"),
            cooking_time=data.get("cook_time"),
            difficulty=None,
        )

        # 1. Parse all ingredients and collect unique names
        parsed_ingredients = []
        unique_names = set()
        for ingredient_str in data.get("ingredients", []):
            quantity, unit, name = _parse_ingredient_string(ingredient_str)
            parsed_ingredients.append((quantity, unit, name))
            unique_names.add(name)

        # 2. Query all existing ingredients in one go
        existing_ingredients = (
            db.query(IngredientModel)
            .filter(IngredientModel.name.in_(unique_names))
            .all()
        )
        name_to_ingredient = {ing.name: ing for ing in existing_ingredients}

        # 3. Find missing names and bulk create them
        missing_names = unique_names - set(name_to_ingredient.keys())
        new_ingredients = [IngredientModel(name=name) for name in missing_names]
        if new_ingredients:
            db.add_all(new_ingredients)
            db.flush()  # Assigns IDs to new ingredients
            for ing in new_ingredients:
                name_to_ingredient[ing.name] = ing

        # 4. Create RecipeIngredient objects using the mapping
        recipe.ingredients = []
        for quantity, unit, name in parsed_ingredients:
            ingredient = name_to_ingredient[name]
            recipe.ingredients.append(
                RecipeIngredient(
                    ingredient_id=ingredient.ingredient_id,
                    quantity=quantity,
                    unit=unit.value if unit else None,
                    is_optional=False,
                ),
            )

        # Add steps
        recipe.steps = [
            RecipeStep(
                step_number=i + 1,
                instruction=step,
            )
            for i, step in enumerate(data.get("instructions_list", []))
        ]

        try:
            db.add(recipe)
            db.commit()
            db.refresh(recipe)
            _log.debug("Recipe added to database: {}", recipe)
        except Exception as e:
            db.rollback()
            _log.exception("Error saving recipe to database", e)
            raise

        # Convert to Pydantic schema for response
        try:
            recipe_schema = RecipeSchema.from_db_model(recipe)
            _log.debug("Converted recipe to response schema: {}", recipe_schema)
            return CreateRecipeResponse(recipe=recipe_schema)
        except Exception as e:
            _log.exception("Error converting recipe ORM to response schema", e)
            raise HTTPException(
                status_code=500,
                detail="Failed to convert recipe to response schema.",
            ) from e

    def get_popular_recipes(
        self,
        pagination: PaginationParams,
    ) -> PopularRecipesResponse:
        """Generate a list of popular recipes from the internet.

        Args:
            pagination (PaginationParams): Pagination params for response control.

        Returns:
            PopularRecipesResponse: The created popular recipe data.
        """
        _log.info(
            "Generating popular recipes (limit={} | offset={} | count_only={})",
            pagination.limit,
            pagination.offset,
            pagination.count_only,
        )

        popular_recipes: list[WebRecipe] = []

        recipe_blog_urls = settings.popular_recipe_urls

        for url in recipe_blog_urls:
            try:
                _log.debug("Scraping popular recipes from URL: {}", url)
                scraped_recipes = scrape_popular_recipes(url)
                _log.debug("Scraped recipes: {}", scraped_recipes)
                popular_recipes.extend(scraped_recipes)
            except RecipeScrapingError as e:
                _log.error(
                    "Failed to scrape popular recipes from URL '{}': {}",
                    url,
                    e,
                )
                continue

        response = PopularRecipesResponse.from_all(
            popular_recipes,
            pagination,
        )
        _log.debug(
            "Generated PopularRecipesResponse: {}",
            response,
        )
        return response

    def get_recommended_substitutions(
        self,
        ingredient_id: int,
        quantity: QuantitySchema | None,
        pagination: PaginationParams,
    ) -> RecommendedSubstitutionsResponse:
        """Generate a list of recommended substitutions from the internet.

        Args:
            ingredient_id (int): The ID of the ingredient to process.
            quantity (Quantity): The quantity of the ingredient to process.
            pagination (PaginationParams): Pagination params for response control.

        Returns:
            RecommendedSubstitutionsResponse: The created recommended recipe data.
        """
        _log.info(
            "Getting recommended substitutions for Ingredient ID {} (limit={} | \
              offset={} | count_only={})",
            ingredient_id,
            pagination.limit,
            pagination.offset,
            pagination.count_only,
        )

        recommended_substitutions = [
            IngredientSubstitution(
                ingredient="Ingredient Substitution 1",
                quantity=quantity,
            ),
            IngredientSubstitution(
                ingredient="Ingredient Substitution 2",
                quantity=quantity,
            ),
            IngredientSubstitution(
                ingredient="Ingredient Substitution 3",
                quantity=quantity,
            ),
            IngredientSubstitution(
                ingredient="Ingredient Substitution 4",
                quantity=quantity,
            ),
            IngredientSubstitution(
                ingredient="Ingredient Substitution 5",
                quantity=quantity,
            ),
            IngredientSubstitution(
                ingredient="Ingredient Substitution 6",
                quantity=quantity,
            ),
            IngredientSubstitution(
                ingredient="Ingredient Substitution 7",
                quantity=quantity,
            ),
            IngredientSubstitution(
                ingredient="Ingredient Substitution 8",
                quantity=quantity,
            ),
            IngredientSubstitution(
                ingredient="Ingredient Substitution 9",
                quantity=quantity,
            ),
            IngredientSubstitution(
                ingredient="Ingredient Substitution 10",
                quantity=quantity,
            ),
        ]

        return RecommendedSubstitutionsResponse.from_all(
            IngredientSchema(
                ingredient_id=ingredient_id,
                quantity=quantity,
            ),
            recommended_substitutions,
            pagination,
        )

    def get_pairing_suggestions(
        self,
        recipe_id: int,
        pagination: PaginationParams,
    ) -> PairingSuggestionsResponse:
        """Identify suggested pairings for the given recipe.

        Args:
            recipe_id (int): The ID of the ingredient.
            pagination (PaginationParams): Pagination params for response control.

        Returns:
            PairingSuggestionsResponse: The generated list of suggested pairings.
        """
        pairing_suggestions = [
            WebRecipe(
                recipe_name="Dummy Recipe 1",
                url="https://some-url.com/dummy-recipe-1",
            ),
            WebRecipe(
                recipe_name="Dummy Recipe 2",
                url="https://some-url.com/dummy-recipe-2",
            ),
            WebRecipe(
                recipe_name="Dummy Recipe 3",
                url="https://some-url.com/dummy-recipe-3",
            ),
            WebRecipe(
                recipe_name="Dummy Recipe 4",
                url="https://some-url.com/dummy-recipe-4",
            ),
            WebRecipe(
                recipe_name="Dummy Recipe 5",
                url="https://some-url.com/dummy-recipe-5",
            ),
            WebRecipe(
                recipe_name="Dummy Recipe 6",
                url="https://some-url.com/dummy-recipe-6",
            ),
            WebRecipe(
                recipe_name="Dummy Recipe 7",
                url="https://some-url.com/dummy-recipe-7",
            ),
            WebRecipe(
                recipe_name="Dummy Recipe 8",
                url="https://some-url.com/dummy-recipe-8",
            ),
            WebRecipe(
                recipe_name="Dummy Recipe 9",
                url="https://some-url.com/dummy-recipe-9",
            ),
            WebRecipe(
                recipe_name="Dummy Recipe 10",
                url="https://some-url.com/dummy-recipe-10",
            ),
        ]

        return PairingSuggestionsResponse.from_all(
            recipe_id,
            pairing_suggestions,
            pagination,
        )
