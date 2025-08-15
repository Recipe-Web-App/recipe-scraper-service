"""Response schema representing shopping information for an ingredient."""

from decimal import Decimal

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.enums.ingredient_unit_enum import IngredientUnitEnum


class IngredientShoppingInfoResponse(BaseSchema):
    """Response schema representing shopping information for an ingredient.

    Attributes:
        ingredient_name (str): The name of the ingredient.
        quantity (Decimal): The quantity of the ingredient.
        unit (IngredientUnitEnum): The unit of measurement for the ingredient.
        estimated_price (Decimal): The estimated price with 2 decimal places.
    """

    ingredient_name: str = Field(..., description="The name of the ingredient")
    quantity: Decimal = Field(..., description="The quantity of the ingredient", ge=0)
    unit: IngredientUnitEnum = Field(
        ..., description="The unit of measurement for the ingredient"
    )
    estimated_price: Decimal = Field(
        ..., description="The estimated price of the ingredient", ge=0, decimal_places=2
    )
