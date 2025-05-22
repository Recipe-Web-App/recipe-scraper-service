"""Recipe scraper service module.

Provides functionality to retrieve detailed recipe information from the internet using
recipe_scraper and beautiful_soup.

Includes logging for traceability and debugging.
"""

from fastapi.responses import JSONResponse
from recipe_scrapers import scrape_me

from app.core.logging import get_logger
from app.schemas.common.ingredient import Ingredient, Quantity
from app.schemas.common.pagination_params import PaginationParams
from app.schemas.common.web_recipe import WebRecipe
from app.schemas.response.pairing_suggestions_response import PairingSuggestionsResponse
from app.schemas.response.recommended_recipes_reponse import PopularRecipesResponse
from app.schemas.response.recommended_substitutions_response import (
    IngredientSubstitution,
    RecommendedSubstitutionsResponse,
)


class RecipeScraperService:
    """Service to retrieve recipe information by scraping data from websites.

    This service provides methods to obtain detailed recipe data using recipe_scraper
        and beautiful_soup.

    Attributes:
        log (logging.Logger): Logger instance for this service.
    """

    def __init__(self) -> None:
        """Initialize the RecipeScraperService with a logger."""
        self.__log = get_logger("RecipeScraperService")

    def create_recipe(self, url: str) -> JSONResponse:
        """Create a recipe from the given URL using recipe_scraper.

        Args:
            url (str): The URL to extract the recipe from.

        Returns:
            JSONResponse: The created recipe data.
        """
        # TODO(jsamuelsen): Change return type to CreateRecipeResponse after testing
        self.__log.info("Creating recipe from URL: %s", url)

        scraper = scrape_me(url)
        self.__log.info("Scraped Recipe: %s", scraper.to_json)

        return JSONResponse(scraper.to_json)

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
        self.__log.info(
            "Generating popular recipes (limit=%s | offset=%s | count_only=%s)",
            pagination.limit,
            pagination.offset,
            pagination.count_only,
        )

        popular_recipes = [
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

        return PopularRecipesResponse.from_all(
            popular_recipes,
            pagination,
        )

    def get_recommended_substitutions(
        self,
        ingredient_id: int,
        quantity: Quantity | None,
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
        self.__log.info(
            "Getting recommended substitutions for Ingredient ID %s (limit=%s | \
              offset=%s | count_only=%s)",
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
            Ingredient(
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
