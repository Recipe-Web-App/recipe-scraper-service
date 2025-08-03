"""Common Recipe schema.

Defines the base data model for a recipe including its list of ingredients.
"""

from datetime import datetime

from pydantic import Field

from app.api.v1.schemas.base_schema import BaseSchema
from app.api.v1.schemas.common.ingredient import Ingredient, Quantity
from app.core.logging import get_logger
from app.db.models.recipe_models import Recipe as RecipeModel
from app.enums.ingredient_unit_enum import IngredientUnitEnum

_log = get_logger(__name__)


class Recipe(BaseSchema):
    """Represents a recipe with all relevant fields."""

    recipe_id: int | None = Field(
        None,
        description="Unique ID of the recipe",
    )
    title: str = Field(
        ...,
        description="Title of the recipe",
    )
    description: str | None = Field(
        None,
        description="Description of the recipe",
    )
    origin_url: str | None = Field(
        None,
        description="Original source URL",
    )
    servings: float | None = Field(
        None,
        description="Number of servings",
    )
    preparation_time: int | None = Field(
        None,
        description="Preparation time in minutes",
    )
    cooking_time: int | None = Field(
        None,
        description="Cooking time in minutes",
    )
    difficulty: str | None = Field(
        None,
        description="Difficulty level",
    )
    ingredients: list[Ingredient] = Field(
        ...,
        description="List of ingredients",
    )
    steps: list["Recipe.RecipeStep"] = Field(
        ...,
        description="List of preparation steps",
    )

    @classmethod
    def from_db_model(cls, recipe: RecipeModel) -> "Recipe":
        """Convert ORM model to Pydantic model, handling nested ingredients.

        Args:     recipe (RecipeModel): The ORM model instance representing the recipe.

        Returns:     CreateRecipeResponse: An instance of CreateRecipeResponse with the
        given         recipe data.
        """
        # If already a mapped dict, return as is
        if isinstance(recipe, dict):
            return cls(**recipe)

        # Manually map ingredients to handle nested Quantity
        _log.trace("Raw recipe.ingredients: {}", getattr(recipe, "ingredients", None))
        ingredients = [
            Ingredient(
                ingredient_id=ingredient.ingredient_id,
                name=getattr(getattr(ingredient, "ingredient", None), "name", None),
                quantity=Quantity(
                    amount=float(getattr(ingredient, "quantity", 0.0)),
                    measurement=(
                        IngredientUnitEnum(ingredient.unit)
                        if ingredient.unit
                        else IngredientUnitEnum.UNIT
                    ),
                ),
            )
            for ingredient in getattr(recipe, "ingredients", [])
        ]
        _log.trace("Mapped ingredients: {}", ingredients)

        data = vars(recipe).copy()
        data.pop("_sa_instance_state", None)
        data["ingredients"] = ingredients
        data["servings"] = (
            float(recipe.servings) if recipe.servings is not None else None
        )

        # Trim out extra fields and log what is dropped
        allowed_fields = set(cls.model_fields)
        dropped = {k: v for k, v in data.items() if k not in allowed_fields}
        if dropped:
            _log.trace(
                "Dropping extra fields from recipe ORM: {}",
                list(dropped.keys()),
            )
        filtered_data = {k: v for k, v in data.items() if k in allowed_fields}
        return cls(**filtered_data)

    class RecipeStep(BaseSchema):
        """Represents a single step in the recipe preparation."""

        step_number: int = Field(
            ...,
            description="Step number in the recipe",
        )
        instruction: str = Field(
            ...,
            description="Instruction for this step",
        )
        optional: bool = Field(
            default=False,
            description="Whether this step is optional",
        )
        timer_seconds: int | None = Field(
            None,
            description="Optional timer in seconds",
        )
        created_at: datetime | None = Field(
            None,
            description="Timestamp when the step was created",
        )
