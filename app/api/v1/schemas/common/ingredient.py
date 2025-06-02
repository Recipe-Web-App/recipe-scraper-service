"""Common ingredient schemas.

Defines Pydantic models related to ingredient data structures shared between request and
response schemas.
"""

from enum import Enum

from pydantic import BaseModel, Field


class Measurement(str, Enum):
    """Enumeration of common measurement units for ingredients.

    Inherits from:
        str: Allows enum values to behave like strings.
        Enum: Enables creation of enumerated constants.

    Members:
        GRAM (str): Grams
        KILOGRAM (str): Kilograms
        MILLIGRAM (str): Milligrams
        LITER (str): Liters
        MILLILITER (str): Milliliters
        CUP (str): Cups
        TABLESPOON (str): Tablespoons
        TEASPOON (str): Teaspoons
        OUNCE (str): Ounces
        POUND (str): Pounds
        PIECE (str): A single unit or item
        SLICE (str): Slices
        PINCH (str): Small pinch, typically for spices
        DASH (str): Very small amount, usually liquid
        UNIT (str): Generic catch-all unit
    """

    GRAM = "gram"
    KILOGRAM = "kilogram"
    MILLIGRAM = "milligram"
    LITER = "liter"
    MILLILITER = "milliliter"
    CUP = "cup"
    TABLESPOON = "tablespoon"
    TEASPOON = "teaspoon"
    OUNCE = "ounce"
    POUND = "pound"
    PIECE = "piece"
    SLICE = "slice"
    PINCH = "pinch"
    DASH = "dash"
    UNIT = "unit"


class Quantity(BaseModel):
    """Sub-schema for ingredient quantity.

    Inherits from:
        BaseModel: Pydantic base class for data validation.

    Attributes:
        quantity_value (float): The numeric value of the ingredient quantity.
        measurement (Measurement): The measurement unit for the quantity.
    """

    quantity_value: float = Field(
        ...,
        description="The numeric value of the ingredient quantity",
    )
    measurement: Measurement = Field(
        ...,
        description="The measurement unit for the quantity",
    )


class Ingredient(BaseModel):
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
