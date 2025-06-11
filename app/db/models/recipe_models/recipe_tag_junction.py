"""Recipe Tag Junction model definition.

Defines the data model for a recipe tag junction entity, including its attributes and
any associated ORM configurations.
"""

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base_database_model import BaseDatabaseModel

if TYPE_CHECKING:
    from app.db.models.recipe_models.recipe import Recipe
    from app.db.models.recipe_models.recipe_tag import RecipeTag


class RecipeTagJunction(BaseDatabaseModel):
    """SQLAlchemy ORM model for the 'recipe_tag_junction' table.

    Represents the many-to-many relationship between recipes and tags.
    """

    __tablename__ = "recipe_tag_junction"
    __table_args__ = ({"schema": "recipe_manager"},)

    recipe_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("recipe_manager.recipes.recipe_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    tag_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("recipe_manager.recipe_tags.tag_id"),
        primary_key=True,
        nullable=False,
    )

    recipe: Mapped["Recipe"] = relationship(
        "Recipe",
        back_populates="tags",
        lazy="joined",
    )
    tag: Mapped["RecipeTag"] = relationship(
        "RecipeTag",
        back_populates="recipe_junctions",
        lazy="joined",
    )
