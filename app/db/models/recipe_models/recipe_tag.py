"""Recipe Tag model definition.

Defines the data model for a recipe tag entity, including its attributes and any
associated ORM configurations.
"""

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base_database_model import BaseDatabaseModel

if TYPE_CHECKING:
    from app.db.models.recipe_models.recipe_tag_junction import RecipeTagJunction


class RecipeTag(BaseDatabaseModel):
    """SQLAlchemy ORM model for the 'recipe_tags' table.

    Represents a recipe tag entity with attributes corresponding to the database schema.
    """

    __tablename__ = "recipe_tags"
    __table_args__ = ({"schema": "recipe_manager"},)

    tag_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )

    recipe_junctions: Mapped[list["RecipeTagJunction"]] = relationship(
        "RecipeTagJunction",
        back_populates="tag",
        cascade="all, delete-orphan",
        lazy="joined",
    )
