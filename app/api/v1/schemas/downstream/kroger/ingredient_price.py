from decimal import Decimal

from pydantic import BaseModel, Field


class KrogerIngredientPrice(BaseModel):
    """Schema for Kroger ingredient price response."""

    ingredient_name: str = Field(..., description="Name of the ingredient searched")
    price: Decimal = Field(..., description="Regular price of the ingredient")
    unit: str = Field(..., description="Unit of measurement (e.g., 'oz', 'lb')")
    location_id: str | None = Field(None, description="Store location ID")
    product_id: str | None = Field(None, description="Kroger product ID")
