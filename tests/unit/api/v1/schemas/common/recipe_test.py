"""Unit tests for the Recipe and RecipeStep schemas as well as their logic."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.common.ingredient import Ingredient, Quantity
from app.api.v1.schemas.common.recipe import Recipe as RecipeSchema
from app.db.models.recipe_models import Recipe as RecipeModel
from app.enums.ingredient_unit_enum import IngredientUnitEnum

_recipe_field_list = list(RecipeSchema.model_fields.keys())
_step_field_list = list(RecipeSchema.RecipeStep.model_fields.keys())


@pytest.mark.unit
def test_recipe_instantiation() -> None:
    """Test Recipe can be instantiated with all fields."""
    # Arrange
    recipe_id = 1
    title = "Tomato Soup"
    description = "A classic soup."
    origin_url = "https://example.com/recipe"
    servings = 4.0
    preparation_time = 10
    cooking_time = 30
    difficulty = "Easy"
    ingredients = [
        Ingredient(
            ingredient_id=1,
            name="Tomato",
            quantity=Quantity(amount=2.0, measurement=IngredientUnitEnum.UNIT),
        ),
        Ingredient(
            ingredient_id=2,
            name="Salt",
            quantity=Quantity(amount=1.0, measurement=IngredientUnitEnum.G),
        ),
    ]
    steps = [
        RecipeSchema.RecipeStep(step_number=1, instruction="Chop tomatoes."),
        RecipeSchema.RecipeStep(step_number=2, instruction="Simmer with salt."),
    ]

    # Act
    recipe = RecipeSchema(
        recipe_id=recipe_id,
        title=title,
        description=description,
        origin_url=origin_url,
        servings=servings,
        preparation_time=preparation_time,
        cooking_time=cooking_time,
        difficulty=difficulty,
        ingredients=ingredients,
        steps=steps,
    )

    # Assert
    assert recipe.recipe_id == recipe_id
    assert recipe.title == title
    assert recipe.description == description
    assert recipe.origin_url == origin_url
    assert recipe.servings == servings
    assert recipe.preparation_time == preparation_time
    assert recipe.cooking_time == cooking_time
    assert recipe.difficulty == difficulty
    assert recipe.ingredients == ingredients
    assert recipe.steps == steps


@pytest.mark.unit
def test_recipe_step_instantiation() -> None:
    """Test RecipeStep can be instantiated with all fields."""
    # Arrange
    step_number = 1
    instruction = "Chop onions."
    optional = True
    timer_seconds = 120
    created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

    # Act
    step = RecipeSchema.RecipeStep(
        step_number=step_number,
        instruction=instruction,
        optional=optional,
        timer_seconds=timer_seconds,
        created_at=created_at,
    )

    # Assert
    assert step.step_number == step_number
    assert step.instruction == instruction
    assert step.optional is True
    assert step.timer_seconds == timer_seconds
    assert step.created_at == created_at


@pytest.mark.unit
def test_recipe_model_copy() -> None:
    """Test that model_copy produces a new, equal Recipe object."""
    # Arrange
    recipe = RecipeSchema(
        recipe_id=1,
        title="Tomato Soup",
        description="A classic soup.",
        origin_url="https://example.com/recipe",
        servings=4.0,
        preparation_time=10,
        cooking_time=30,
        difficulty="Easy",
        ingredients=[
            Ingredient(
                ingredient_id=1,
                name="Tomato",
                quantity=Quantity(amount=2.0, measurement=IngredientUnitEnum.UNIT),
            ),
        ],
        steps=[RecipeSchema.RecipeStep(step_number=1, instruction="Chop tomatoes.")],
    )

    # Act
    recipe_copy = recipe.model_copy()

    # Assert
    assert recipe == recipe_copy
    assert recipe is not recipe_copy
    for field in _recipe_field_list:
        assert getattr(recipe, field) == getattr(recipe_copy, field)


@pytest.mark.unit
def test_recipe_step_model_copy() -> None:
    """Test that model_copy produces a new, equal RecipeStep object."""
    # Arrange
    step = RecipeSchema.RecipeStep(
        step_number=1,
        instruction="Mix ingredients.",
        optional=False,
        timer_seconds=60,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )

    # Act
    step_copy = step.model_copy()

    # Assert
    assert step == step_copy
    assert step is not step_copy
    for field in _step_field_list:
        assert getattr(step, field) == getattr(step_copy, field)


@pytest.mark.unit
def test_recipe_equality() -> None:
    """Test that two Recipe objects with the same data are equal."""
    # Arrange
    kwargs1 = {
        "recipe_id": 1,
        "title": "Tomato Soup",
        "description": "A classic soup.",
        "origin_url": "https://example.com/recipe",
        "servings": 4.0,
        "preparation_time": 10,
        "cooking_time": 30,
        "difficulty": "Easy",
        "ingredients": [
            Ingredient(
                ingredient_id=1,
                name="Tomato",
                quantity=Quantity(amount=2.0, measurement=IngredientUnitEnum.UNIT),
            ),
        ],
        "steps": [RecipeSchema.RecipeStep(step_number=1, instruction="Chop tomatoes.")],
    }
    kwargs2 = {
        "recipe_id": 2,
        "title": "Potato Soup",
        "description": "A different soup.",
        "origin_url": "https://example.com/other",
        "servings": 2.0,
        "preparation_time": 5,
        "cooking_time": 15,
        "difficulty": "Medium",
        "ingredients": [
            Ingredient(
                ingredient_id=2,
                name="Potato",
                quantity=Quantity(amount=3.0, measurement=IngredientUnitEnum.UNIT),
            ),
        ],
        "steps": [RecipeSchema.RecipeStep(step_number=1, instruction="Chop potatoes.")],
    }

    # Act
    r1 = RecipeSchema(**kwargs1)
    r2 = RecipeSchema(**kwargs1)
    r3 = RecipeSchema(**kwargs2)

    # Assert
    assert r1 == r2
    assert r1 != r3


@pytest.mark.unit
def test_recipe_step_equality() -> None:
    """Test that two RecipeStep objects with the same data are equal."""
    # Arrange
    kwargs1 = {
        "step_number": 1,
        "instruction": "Mix ingredients.",
        "optional": False,
        "timer_seconds": 60,
        "created_at": datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    }
    kwargs2 = {
        "step_number": 2,
        "instruction": "Bake.",
        "optional": True,
        "timer_seconds": 180,
        "created_at": datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC),
    }

    # Act
    s1 = RecipeSchema.RecipeStep(**kwargs1)
    s2 = RecipeSchema.RecipeStep(**kwargs1)
    s3 = RecipeSchema.RecipeStep(**kwargs2)

    # Assert
    assert s1 == s2
    assert s1 != s3


@pytest.mark.unit
def test_recipe_serialization() -> None:
    """Test that model_dump produces a serializable dict with all fields."""
    # Arrange
    recipe = RecipeSchema(
        recipe_id=1,
        title="Tomato Soup",
        description="A classic soup.",
        origin_url="https://example.com/recipe",
        servings=4.0,
        preparation_time=10,
        cooking_time=30,
        difficulty="Easy",
        ingredients=[
            Ingredient(
                ingredient_id=1,
                name="Tomato",
                quantity=Quantity(amount=2.0, measurement=IngredientUnitEnum.UNIT),
            ),
        ],
        steps=[RecipeSchema.RecipeStep(step_number=1, instruction="Chop tomatoes.")],
    )

    # Act
    data = recipe.model_dump()

    # Assert
    assert isinstance(data, dict)
    for field in _recipe_field_list:
        if field == "ingredients":
            assert data[field] == [i.model_dump() for i in recipe.ingredients]
        elif field == "steps":
            assert data[field] == [s.model_dump() for s in recipe.steps]
        else:
            assert data[field] == getattr(recipe, field)


@pytest.mark.unit
def test_recipe_step_serialization() -> None:
    """Test that model_dump produces a serializable dict with all fields."""
    # Arrange
    step = RecipeSchema.RecipeStep(
        step_number=1,
        instruction="Mix ingredients.",
        optional=False,
        timer_seconds=60,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )

    # Act
    data = step.model_dump()

    # Assert
    assert isinstance(data, dict)
    for field in _step_field_list:
        assert data[field] == getattr(step, field)


@pytest.mark.unit
def test_recipe_deserialization() -> None:
    """Test that model_validate reconstructs a Recipe object from dict."""
    # Arrange
    data = {
        "recipe_id": 1,
        "title": "Tomato Soup",
        "description": "A classic soup.",
        "origin_url": "https://example.com/recipe",
        "servings": 4.0,
        "preparation_time": 10,
        "cooking_time": 30,
        "difficulty": "Easy",
        "ingredients": [
            Ingredient(
                ingredient_id=1,
                name="Tomato",
                quantity=Quantity(amount=2.0, measurement=IngredientUnitEnum.UNIT),
            ),
        ],
        "steps": [RecipeSchema.RecipeStep(step_number=1, instruction="Chop tomatoes.")],
    }

    # Act
    recipe = RecipeSchema.model_validate(data)

    # Assert
    assert isinstance(recipe, RecipeSchema)
    for field in _recipe_field_list:
        assert getattr(recipe, field) == data[field]


@pytest.mark.unit
def test_recipe_step_deserialization() -> None:
    """Test that model_validate reconstructs a RecipeStep object from dict."""
    # Arrange
    data = {
        "step_number": 1,
        "instruction": "Mix ingredients.",
        "optional": False,
        "timer_seconds": 60,
        "created_at": datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    }

    # Act
    step = RecipeSchema.RecipeStep.model_validate(data)

    # Assert
    assert isinstance(step, RecipeSchema.RecipeStep)
    for field in _step_field_list:
        assert getattr(step, field) == data[field]


@pytest.mark.unit
def test_recipe_default_values() -> None:
    """Test Recipe can be instantiated with default values for optional fields."""
    # Arrange
    title = "Simple Recipe"
    ingredients = [
        Ingredient(
            ingredient_id=1,
            name="Tomato",
            quantity=Quantity(amount=2.0, measurement=IngredientUnitEnum.UNIT),
        ),
    ]
    steps = [RecipeSchema.RecipeStep(step_number=1, instruction="Chop tomatoes.")]

    # Act
    recipe = RecipeSchema(title=title, ingredients=ingredients, steps=steps)

    # Assert
    assert recipe.recipe_id is None
    assert recipe.description is None
    assert recipe.origin_url is None
    assert recipe.servings is None
    assert recipe.preparation_time is None
    assert recipe.cooking_time is None
    assert recipe.difficulty is None
    assert recipe.title == title
    assert recipe.ingredients == ingredients
    assert recipe.steps == steps


@pytest.mark.unit
def test_recipe_step_default_values() -> None:
    """Test RecipeStep can be instantiated with default values."""
    # Arrange and Act
    step = RecipeSchema.RecipeStep(step_number=1, instruction="Do something.")

    # Assert
    assert step.optional is False
    assert step.timer_seconds is None
    assert step.created_at is None


@pytest.mark.unit
def test_recipe_constraints() -> None:
    """Test Recipe schema constraints."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        RecipeSchema(title="Soup", ingredients=[], steps=[], extra_field=123)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        RecipeSchema(title=123, ingredients=[], steps=[])
    with pytest.raises(ValidationError):
        RecipeSchema(title="Soup", ingredients="not-a-list", steps=[])
    with pytest.raises(ValidationError):
        RecipeSchema(title="Soup", ingredients=[], steps="not-a-list")


@pytest.mark.unit
def test_recipe_step_constraints() -> None:
    """Test RecipeStep schema constraints."""
    # Arrange and Act and Assert
    with pytest.raises(ValidationError):
        RecipeSchema.RecipeStep(
            step_number=1,
            instruction="Do something.",
            extra_field=123,
        )  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        RecipeSchema.RecipeStep(step_number="not-an-int", instruction="Do something.")
    with pytest.raises(ValidationError):
        RecipeSchema.RecipeStep(step_number=1, instruction=12345)


@pytest.mark.unit
def test_recipe_from_db(mock_recipe_model: RecipeModel) -> None:
    """Test conversion from ORM model to Pydantic schema."""
    # Act
    recipe = RecipeSchema.from_db_model(mock_recipe_model)

    # Assert
    assert isinstance(recipe, RecipeSchema)
    for field in _recipe_field_list:
        if field == "ingredients":
            # Compare ingredient_id, name, and quantity fields for each ingredient
            for actual, expected in zip(
                recipe.ingredients,
                mock_recipe_model.ingredients,
                strict=True,
            ):
                assert actual.ingredient_id == expected.ingredient_id
                assert actual.quantity is not None
                assert actual.quantity.amount == expected.quantity
                assert actual.quantity.measurement == expected.unit
        elif field == "steps":
            assert recipe.steps == [
                RecipeSchema.RecipeStep.model_validate(s)
                for s in mock_recipe_model.steps
            ]
        else:
            assert getattr(recipe, field) == getattr(mock_recipe_model, field)
