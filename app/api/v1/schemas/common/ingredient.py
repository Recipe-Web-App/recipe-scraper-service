"""Common ingredient schemas.

Defines Pydantic models related to ingredient data structures shared between request and
response schemas.
"""

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.enums.ingredient_unit_enum import IngredientUnitEnum


class Quantity(BaseSchema):
    """Sub-schema for ingredient quantity.

    Inherits from:     BaseModel: Pydantic base class for data validation.

    Attributes:     amount (float): The numeric value of the ingredient quantity.
    measurement (Measurement): The measurement unit for the quantity.
    """

    amount: float = Field(
        ...,
        description="The numeric value of the ingredient quantity",
        ge=0,
    )
    measurement: IngredientUnitEnum = Field(
        default=IngredientUnitEnum.UNIT,
        description="The measurement unit for the quantity",
    )


class Ingredient(BaseSchema):
    """Common schema for ingredient data.

    Inherits from:     BaseModel: Pydantic base class for data validation.

    Attributes:     ingredient_id (int): The ID of the ingredient.     name (str |
    None): Name of the ingredient.     quantity (Quantity): The quantity details of the
    ingredient.
    """

    ingredient_id: int = Field(..., description="The ID of the ingredient")
    name: str | None = Field(None, description="Name of the ingredient")
    quantity: Quantity | None = Field(
        default=None,
        description="The quantity details of the ingredient",
    )
