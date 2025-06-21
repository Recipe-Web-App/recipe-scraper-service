"""Nutritional Info model definition.

Defines the data model for a nutritional info entity from OpenFoodFacts, including its
attributes and any associated ORM configurations.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ARRAY, BigInteger, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base_database_model import BaseDatabaseModel
from app.enums.allergy import Allergy
from app.enums.ingredient_unit_enum import IngredientUnitEnum


class NutritionalInfo(BaseDatabaseModel):
    """SQLAlchemy ORM model for the 'nutritional_info' table.

    Represents nutritional information from OpenFoodFacts with attributes corresponding
    to the database schema.
    """

    __tablename__ = "nutritional_info"
    __table_args__ = ({"schema": "recipe_manager"},)

    # Primary key and identifiers
    nutritional_info_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    code: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    # Basic product information
    product_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    generic_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    brands: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    categories: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    serving_quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )
    serving_measurement: Mapped[IngredientUnitEnum | None] = mapped_column(
        SAEnum(
            IngredientUnitEnum,
            name="ingredient_unit_enum",
            schema="recipe_manager",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=True,
    )

    # Allergens (stored as PostgreSQL enum array)
    allergens: Mapped[list[Allergy] | None] = mapped_column(
        ARRAY(
            SAEnum(
                Allergy,
                values_callable=lambda enum_cls: [e.value for e in enum_cls],
            ),
        ),
        nullable=True,
    )

    food_groups: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Classification scores
    nutriscore_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    nutriscore_grade: Mapped[str | None] = mapped_column(
        String(5),
        nullable=True,
    )

    # MacroNutrients (per 100g)
    energy_kcal_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )
    carbohydrates_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )
    cholesterol_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )
    proteins_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )

    # Sugars
    sugars_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )
    added_sugars_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )

    # Fats
    fat_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )
    saturated_fat_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )
    monounsaturated_fat_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )
    polyunsaturated_fat_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )
    omega_3_fat_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )
    omega_6_fat_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )
    omega_9_fat_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )
    trans_fat_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )

    # Fibers
    fiber_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )
    soluble_fiber_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )
    insoluble_fiber_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3),
        nullable=True,
    )

    # Vitamins (higher precision for smaller values)
    vitamin_a_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    vitamin_b6_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    vitamin_b12_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    vitamin_c_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    vitamin_d_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    vitamin_e_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    vitamin_k_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )

    # Minerals (higher precision for smaller values)
    calcium_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    iron_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    magnesium_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    potassium_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    sodium_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    zinc_100g: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
