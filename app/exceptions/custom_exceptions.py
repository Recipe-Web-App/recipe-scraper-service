"""Custom exception classes.

Defines application-specific exceptions used to handle error cases with meaningful
messages.
"""

from app.enums.ingredient_unit_enum import IngredientUnitEnum


class IncompatibleUnitsError(ValueError):
    """Raised when attempting to convert between incompatible measurement units.

    This exception is raised when trying to perform unit conversions between units that
    cannot be meaningfully converted (e.g., grams to milliliters).
    """

    def __init__(
        self,
        from_unit: IngredientUnitEnum,
        to_unit: IngredientUnitEnum,
    ) -> None:
        """Initialize the exception with unit information.

        Args:
            from_unit: The source unit that cannot be converted
            to_unit: The target unit that cannot be converted to
        """
        self.from_unit = from_unit
        self.to_unit = to_unit
        super().__init__(f"Cannot convert between {from_unit} and {to_unit}")

    def get_from_unit(self) -> IngredientUnitEnum:
        """Get the source unit that caused the error.

        Returns:
            IngredientUnitEnum: The unit that conversion was attempted from.
        """
        return self.from_unit

    def get_to_unit(self) -> IngredientUnitEnum:
        """Get the target unit that caused the error.

        Returns:
            IngredientUnitEnum: The unit that conversion was attempted to.
        """
        return self.to_unit


class RecipeScrapingError(Exception):
    """Raised when a recipe URL cannot be scraped or processed.

    This exception is raised when:
    - The URL is invalid or malformed
    - The recipe blog/website is not compatible with the scraper
    - The website structure prevents successful scraping
    - Network or access issues prevent scraping
    """

    def __init__(self, url: str, reason: str | None = None) -> None:
        """Initialize the exception with the URL and optional reason.

        Args:
            url: The URL that could not be scraped.
            reason: Optional specific reason for the scraping failure.
        """
        self.url = url
        self.reason = reason

        if reason:
            message = f"Failed to scrape recipe from {url}: {reason}"
        else:
            message = f"Failed to scrape recipe from {url}"

        super().__init__(message)

    def get_url(self) -> str:
        """Get the URL that caused the error.

        Returns:
            str: The URL that could not be scraped.
        """
        return self.url

    def get_reason(self) -> str | None:
        """Get the specific reason for the scraping failure.

        Returns:
            str | None: The reason for failure, if provided.
        """
        return self.reason


class SubstitutionNotFoundError(Exception):
    """Raised when no substitutes can be found for an ingredient.

    This exception is raised when:
    - The external substitution service has no data for the ingredient
    - The ingredient is too specific or rare to have common substitutes
    - The substitution service API returns a "no results" response
    """

    def __init__(self, ingredient_name: str, reason: str | None = None) -> None:
        """Initialize the exception with the ingredient name and optional reason.

        Args:
            ingredient_name: The name of the ingredient that has no substitutes.
            reason: Optional specific reason why no substitutes were found.
        """
        self.ingredient_name = ingredient_name
        self.reason = reason

        if reason:
            message = f"No substitutes found for '{ingredient_name}': {reason}"
        else:
            message = f"No substitutes found for '{ingredient_name}'"

        super().__init__(message)

    def get_ingredient_name(self) -> str:
        """Get the ingredient name that caused the error.

        Returns:
            str: The ingredient name that has no substitutes.
        """
        return self.ingredient_name

    def get_reason(self) -> str | None:
        """Get the specific reason why no substitutes were found.

        Returns:
            str | None: The reason for no substitutes, if provided.
        """
        return self.reason
