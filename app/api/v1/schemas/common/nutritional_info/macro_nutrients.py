"""Contains schema definition for macro-nutrient nutritional information."""

from decimal import Decimal

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.api.v1.schemas.common.nutritional_info.fats import Fats
from app.api.v1.schemas.common.nutritional_info.fibers import Fibers
from app.api.v1.schemas.common.nutritional_info.sugars import Sugars
from app.utils.aggregation_helpers import sum_decimal_optional, sum_int_optional


class MacroNutrients(BaseSchema):
    """Contains macro-nutrient information for an ingredient.

    Attributes:     calories (int | None): Total calories per serving.     carbs_g
    (Decimal | None): Carbohydrate content in grams.     cholesterol_mg (Decimal |
    None): Cholesterol content in milligrams, if         available.     protein_g
    (Decimal | None): Protein content in grams.     sugars (Sugars): Sugar information.
    fats (Fats): Fat information.     fibers (Fibers): Fiber information.
    """

    calories: int | None = Field(
        None,
        ge=0,
        description="Total calories per serving",
    )
    carbs_g: Decimal | None = Field(
        None,
        ge=0,
        description="Carbohydrate content in grams",
    )
    cholesterol_mg: Decimal | None = Field(
        None,
        ge=0,
        description="Cholesterol content in milligrams",
    )
    protein_g: Decimal | None = Field(
        None,
        ge=0,
        description="Protein content in grams",
    )
    sugars: Sugars = Field(
        default_factory=Sugars,
        description="Sugar information",
    )
    fats: Fats = Field(
        default_factory=Fats,
        description="Fat information",
    )
    fibers: Fibers = Field(
        default_factory=Fibers,
        description="Fiber information",
    )

    def __add__(self, other: "MacroNutrients") -> "MacroNutrients":
        """Combine all macro-nutrient values from two entities.

        Args:     other (MacroNutrients): The other entity to add.

        Returns:     MacroNutrients: A sum of all macro-nutrient data.
        """
        return MacroNutrients(
            calories=sum_int_optional(
                self.calories,
                other.calories,
            ),
            carbs_g=sum_decimal_optional(
                self.carbs_g,
                other.carbs_g,
                "0.001",  # 3 decimal places for macronutrients
            ),
            cholesterol_mg=sum_decimal_optional(
                self.cholesterol_mg,
                other.cholesterol_mg,
                "0.001",  # 3 decimal places for macronutrients
            ),
            protein_g=sum_decimal_optional(
                self.protein_g,
                other.protein_g,
                "0.001",  # 3 decimal places for macronutrients
            ),
            sugars=(self.sugars or Sugars()) + (other.sugars or Sugars()),
            fats=(self.fats or Fats()) + (other.fats or Fats()),
            fibers=(self.fibers or Fibers()) + (other.fibers or Fibers()),
        )
