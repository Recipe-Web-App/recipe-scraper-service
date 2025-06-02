"""Recipe Ingredient model definition.

Defines the data model for a recipe ingredient entity, including its attributes and any
associated ORM configurations.
"""

from decimal import Decimal

from sqlalchemy import BigInteger, Boolean
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base_database_model import BaseDatabaseModel
from app.enums.ingredient_unit_enum import IngredientUnitEnum


class RecipeIngredient(BaseDatabaseModel):
    """SQLAlchemy ORM model for the 'recipe_ingredients' table.

    Represents the association between a recipe and an ingredient, including quantity,
    unit, and whether the ingredient is optional.
    """

    __tablename__ = "recipe_ingredients"
    __table_args__ = ({"schema": "recipe_manager"},)

    recipe_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("recipe_manager.recipes.recipe_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    ingredient_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("recipe_manager.ingredients.ingredient_id"),
        primary_key=True,
        nullable=False,
    )
    quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )
    unit: Mapped[IngredientUnitEnum | None] = mapped_column(
        SAEnum(
            IngredientUnitEnum,
            name="ingredient_unit_enum",
            schema="recipe_manager",
            native_enum=False,
            create_constraint=False,
        ),
        nullable=True,
    )
    is_optional: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
