"""Common ingredient schemas.

Defines Pydantic models related to ingredient data structures shared between request and
response schemas.
"""

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.enums.ingredient_unit_enum import IngredientUnitEnum


class Quantity(BaseSchema):
    """Sub-schema for ingredient quantity.

    Inherits from:
        BaseModel: Pydantic base class for data validation.

    Attributes:
        quantity_value (float): The numeric value of the ingredient quantity.
        measurement (Measurement): The measurement unit for the quantity.
    """

    quantity_value: float | None = Field(
        None,
        description="The numeric value of the ingredient quantity",
    )
    measurement: IngredientUnitEnum = Field(
        default=IngredientUnitEnum.UNIT,
        description="The measurement unit for the quantity",
    )


class Ingredient(BaseSchema):
    """Common schema for ingredient data.

    Inherits from:
        BaseModel: Pydantic base class for data validation.

    Attributes:
        ingredient_id (int): The ID of the ingredient.
        name (str | None): Name of the ingredient.
        quantity (Quantity): The quantity details of the ingredient.
    """

    ingredient_id: int = Field(..., description="The ID of the ingredient")
    name: str | None = Field(None, description="Name of the ingredient")
    quantity: Quantity = Field(
        ...,
        description="The quantity details of the ingredient",
    )
