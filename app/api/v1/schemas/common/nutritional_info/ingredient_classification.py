"""Contains schema definition for ingredient classification nutritional information."""

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.enums.allergen_enum import AllergenEnum
from app.enums.food_group_enum import FoodGroupEnum
from app.utils.aggregation_helpers import (
    combine_nutriscore_grades_optional,
    combine_string_optional,
    sum_int_optional,
    sum_list_optional,
)


class IngredientClassification(BaseSchema):
    """Contains meta and classification information for an ingredient.

    Attributes:
        allergies (list[Allergy]): Key allergy indicators for the ingredient.
        food_groups (list[FoodGroupEnum] | None): Food groups this ingredient belongs
            to.
        nutriscore_score (int | None): Nutri-Score value for the ingredient.
        nutriscore_grade (str | None): Nutri-Score letter grade for the ingredient.
        product_name (str | None): Product name from nutritional database.
        brands (str | None): Brand information from nutritional database.
        categories (str | None): Product categories from nutritional database.
    """

    allergies: list[AllergenEnum] | None = Field(
        None,
        description="List of allergens associated with the ingredient",
    )
    food_groups: list[FoodGroupEnum] | None = Field(
        None,
        description="Food groups this ingredient belongs to",
    )
    nutriscore_score: int | None = Field(
        None,
        ge=1,
        le=5,
        description="Nutri-Score value for the ingredient, between 1 and 5",
    )
    nutriscore_grade: str | None = Field(
        None,
        description="Nutri-Score letter grade (A-E) for the ingredient",
    )
    product_name: str | None = Field(
        None,
        description="Product name from nutritional database",
    )
    brands: str | None = Field(
        None,
        description="Brand information from nutritional database",
    )
    categories: str | None = Field(
        None,
        description="Product categories from nutritional database",
    )

    def __add__(self, other: "IngredientClassification") -> "IngredientClassification":
        """Combine classification values from two entities.

        Args:
            other (IngredientClassification): The other entity to add.

        Returns:
            IngredientClassification: A merged classification.
        """
        return IngredientClassification(
            allergies=sum_list_optional(
                self.allergies,
                other.allergies,
            ),
            food_groups=sum_list_optional(
                self.food_groups,
                other.food_groups,
            ),
            nutriscore_score=sum_int_optional(
                self.nutriscore_score,
                other.nutriscore_score,
            ),
            nutriscore_grade=combine_nutriscore_grades_optional(
                self.nutriscore_grade,
                other.nutriscore_grade,
            ),
            product_name=combine_string_optional(
                self.product_name,
                other.product_name,
            ),
            brands=combine_string_optional(
                self.brands,
                other.brands,
            ),
            categories=combine_string_optional(
                self.categories,
                other.categories,
            ),
        )
