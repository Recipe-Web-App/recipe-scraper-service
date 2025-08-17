"""Response schema representing shopping information for an ingredient."""

from decimal import Decimal

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.api.v1.schemas.common.ingredient import Quantity


class IngredientShoppingInfoResponse(BaseSchema):
    """Response schema representing shopping information for an ingredient.

    Attributes:
        ingredient_name (str): The name of the ingredient.
        quantity (Decimal): The quantity of the ingredient.
        unit (IngredientUnitEnum): The unit of measurement for the ingredient.
        estimated_price (Decimal | None): The estimated price with 2 decimal places,
            or None if pricing unavailable.
    """

    ingredient_name: str = Field(..., description="The name of the ingredient")
    quantity: Quantity = Field(..., description="The quantity of the ingredient")
    estimated_price: Decimal | None = Field(
        None,
        description="The estimated price of the ingredient (None if unavailable)",
        ge=0,
        decimal_places=2,
    )
