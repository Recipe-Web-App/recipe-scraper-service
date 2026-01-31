"""Allergen-related factories for generating test data.

Uses polyfactory for consistent test data generation.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from polyfactory.factories.pydantic_factory import ModelFactory

from app.database.repositories.allergen import AllergenData
from app.schemas.allergen import (
    AllergenDataSource,
    AllergenInfo,
    AllergenPresenceType,
    IngredientAllergenResponse,
    RecipeAllergenResponse,
)
from app.schemas.enums import Allergen


class AllergenInfoFactory(ModelFactory[AllergenInfo]):
    """Factory for generating AllergenInfo instances."""

    __model__ = AllergenInfo

    @classmethod
    def allergen(cls) -> Allergen:
        """Default allergen type."""
        return Allergen.GLUTEN

    @classmethod
    def presence_type(cls) -> AllergenPresenceType:
        """Default presence type."""
        return AllergenPresenceType.CONTAINS

    @classmethod
    def confidence_score(cls) -> float:
        """Default confidence score."""
        return 1.0

    @classmethod
    def gluten(cls, **kwargs: Any) -> AllergenInfo:
        """Create gluten allergen info."""
        return cls.build(
            allergen=Allergen.GLUTEN,
            presence_type=AllergenPresenceType.CONTAINS,
            confidence_score=1.0,
            source_notes="Contains wheat gluten",
            **kwargs,
        )

    @classmethod
    def wheat(cls, **kwargs: Any) -> AllergenInfo:
        """Create wheat allergen info."""
        return cls.build(
            allergen=Allergen.WHEAT,
            presence_type=AllergenPresenceType.CONTAINS,
            confidence_score=1.0,
            source_notes="Made from wheat",
            **kwargs,
        )

    @classmethod
    def milk(cls, **kwargs: Any) -> AllergenInfo:
        """Create milk allergen info."""
        return cls.build(
            allergen=Allergen.MILK,
            presence_type=AllergenPresenceType.CONTAINS,
            confidence_score=1.0,
            source_notes="Dairy product",
            **kwargs,
        )

    @classmethod
    def eggs(cls, **kwargs: Any) -> AllergenInfo:
        """Create eggs allergen info."""
        return cls.build(
            allergen=Allergen.EGGS,
            presence_type=AllergenPresenceType.CONTAINS,
            confidence_score=1.0,
            source_notes="Contains eggs",
            **kwargs,
        )

    @classmethod
    def peanuts(cls, **kwargs: Any) -> AllergenInfo:
        """Create peanuts allergen info."""
        return cls.build(
            allergen=Allergen.PEANUTS,
            presence_type=AllergenPresenceType.CONTAINS,
            confidence_score=1.0,
            source_notes="Contains peanuts",
            **kwargs,
        )

    @classmethod
    def tree_nuts(cls, **kwargs: Any) -> AllergenInfo:
        """Create tree nuts allergen info."""
        return cls.build(
            allergen=Allergen.TREE_NUTS,
            presence_type=AllergenPresenceType.CONTAINS,
            confidence_score=1.0,
            source_notes="Contains tree nuts",
            **kwargs,
        )

    @classmethod
    def may_contain(cls, allergen: Allergen, **kwargs: Any) -> AllergenInfo:
        """Create allergen with MAY_CONTAIN presence type."""
        return cls.build(
            allergen=allergen,
            presence_type=AllergenPresenceType.MAY_CONTAIN,
            confidence_score=0.8,
            source_notes="May contain traces",
            **kwargs,
        )

    @classmethod
    def traces(cls, allergen: Allergen, **kwargs: Any) -> AllergenInfo:
        """Create allergen with TRACES presence type."""
        return cls.build(
            allergen=allergen,
            presence_type=AllergenPresenceType.TRACES,
            confidence_score=0.7,
            source_notes="May contain trace amounts",
            **kwargs,
        )


class IngredientAllergenResponseFactory(ModelFactory[IngredientAllergenResponse]):
    """Factory for generating IngredientAllergenResponse instances."""

    __model__ = IngredientAllergenResponse

    @classmethod
    def ingredient_id(cls) -> int:
        """Default ingredient ID."""
        return 1

    @classmethod
    def ingredient_name(cls) -> str:
        """Default ingredient name."""
        return "test-ingredient"

    @classmethod
    def allergens(cls) -> list[AllergenInfo]:
        """Default allergens list."""
        return []

    @classmethod
    def data_source(cls) -> AllergenDataSource:
        """Default data source."""
        return AllergenDataSource.USDA

    @classmethod
    def overall_confidence(cls) -> float:
        """Default overall confidence."""
        return 1.0

    @classmethod
    def flour(cls, **kwargs: Any) -> IngredientAllergenResponse:
        """Create allergen response for flour (gluten + wheat)."""
        return cls.build(
            ingredient_id=1,
            ingredient_name="flour",
            usda_food_description="Wheat flour, white, all-purpose, enriched",
            allergens=[
                AllergenInfoFactory.gluten(),
                AllergenInfoFactory.wheat(),
            ],
            data_source=AllergenDataSource.USDA,
            overall_confidence=1.0,
            **kwargs,
        )

    @classmethod
    def butter(cls, **kwargs: Any) -> IngredientAllergenResponse:
        """Create allergen response for butter (milk)."""
        return cls.build(
            ingredient_id=2,
            ingredient_name="butter",
            usda_food_description="Butter, salted",
            allergens=[AllergenInfoFactory.milk()],
            data_source=AllergenDataSource.USDA,
            overall_confidence=1.0,
            **kwargs,
        )

    @classmethod
    def eggs_response(cls, **kwargs: Any) -> IngredientAllergenResponse:
        """Create allergen response for eggs."""
        return cls.build(
            ingredient_id=3,
            ingredient_name="eggs",
            usda_food_description="Egg, whole, raw, fresh",
            allergens=[AllergenInfoFactory.eggs()],
            data_source=AllergenDataSource.USDA,
            overall_confidence=1.0,
            **kwargs,
        )

    @classmethod
    def chicken(cls, **kwargs: Any) -> IngredientAllergenResponse:
        """Create allergen response for chicken (no allergens)."""
        return cls.build(
            ingredient_id=4,
            ingredient_name="chicken",
            usda_food_description="Chicken, broiler or fryers, breast, skinless",
            allergens=[],
            data_source=AllergenDataSource.USDA,
            overall_confidence=1.0,
            **kwargs,
        )

    @classmethod
    def from_open_food_facts(
        cls,
        name: str = "test-product",
        allergens: list[AllergenInfo] | None = None,
        **kwargs: Any,
    ) -> IngredientAllergenResponse:
        """Create allergen response from Open Food Facts source."""
        return cls.build(
            ingredient_name=name,
            allergens=allergens or [],
            data_source=AllergenDataSource.OPEN_FOOD_FACTS,
            overall_confidence=0.95,
            **kwargs,
        )

    @classmethod
    def empty(cls, name: str = "unknown", **kwargs: Any) -> IngredientAllergenResponse:
        """Create empty allergen response (no allergens found)."""
        return cls.build(
            ingredient_name=name,
            allergens=[],
            data_source=None,
            overall_confidence=None,
            **kwargs,
        )


class RecipeAllergenResponseFactory(ModelFactory[RecipeAllergenResponse]):
    """Factory for generating RecipeAllergenResponse instances."""

    __model__ = RecipeAllergenResponse

    @classmethod
    def contains(cls) -> list[Allergen]:
        """Default contains list."""
        return []

    @classmethod
    def may_contain(cls) -> list[Allergen]:
        """Default may_contain list."""
        return []

    @classmethod
    def allergens(cls) -> list[AllergenInfo]:
        """Default allergens list."""
        return []

    @classmethod
    def missing_ingredients(cls) -> list[int]:
        """Default missing ingredients list."""
        return []

    @classmethod
    def pancakes(cls, **kwargs: Any) -> RecipeAllergenResponse:
        """Create allergen response for pancakes (flour + eggs + butter)."""
        return cls.build(
            contains=[Allergen.GLUTEN, Allergen.WHEAT, Allergen.MILK, Allergen.EGGS],
            may_contain=[],
            allergens=[
                AllergenInfoFactory.gluten(),
                AllergenInfoFactory.wheat(),
                AllergenInfoFactory.milk(),
                AllergenInfoFactory.eggs(),
            ],
            ingredient_details=None,
            missing_ingredients=[],
            **kwargs,
        )

    @classmethod
    def with_missing(
        cls,
        missing: list[int],
        **kwargs: Any,
    ) -> RecipeAllergenResponse:
        """Create recipe response with missing ingredient IDs."""
        return cls.build(
            contains=[Allergen.GLUTEN],
            may_contain=[],
            allergens=[AllergenInfoFactory.gluten()],
            missing_ingredients=missing,
            **kwargs,
        )

    @classmethod
    def with_details(cls, **kwargs: Any) -> RecipeAllergenResponse:
        """Create recipe response with ingredient details."""
        return cls.build(
            contains=[Allergen.GLUTEN, Allergen.MILK],
            may_contain=[],
            allergens=[
                AllergenInfoFactory.gluten(),
                AllergenInfoFactory.milk(),
            ],
            ingredient_details={
                "flour": IngredientAllergenResponseFactory.flour(),
                "butter": IngredientAllergenResponseFactory.butter(),
            },
            missing_ingredients=[],
            **kwargs,
        )


class AllergenDataFactory:
    """Factory for generating AllergenData DTOs (database rows).

    Not a ModelFactory since AllergenData is a Pydantic BaseModel
    that represents database row data.
    """

    @classmethod
    def build(
        cls,
        ingredient_id: int = 1,
        ingredient_name: str = "test-ingredient",
        usda_food_description: str | None = None,
        allergen_type: str = "GLUTEN",
        presence_type: str = "CONTAINS",
        confidence_score: Decimal | None = None,
        source_notes: str | None = None,
        data_source: str = "USDA",
        profile_confidence: Decimal | None = None,
    ) -> AllergenData:
        """Build an AllergenData instance."""
        return AllergenData(
            ingredient_id=ingredient_id,
            ingredient_name=ingredient_name,
            usda_food_description=usda_food_description
            or f"{ingredient_name.title()}, standard",
            allergen_type=allergen_type,
            presence_type=presence_type,
            confidence_score=confidence_score or Decimal("1.0"),
            source_notes=source_notes,
            data_source=data_source,
            profile_confidence=profile_confidence or Decimal("1.0"),
        )

    @classmethod
    def flour_gluten(
        cls,
        ingredient_id: int = 1,
        source_notes: str = "Contains wheat gluten",
    ) -> AllergenData:
        """Create flour with GLUTEN allergen."""
        return cls.build(
            ingredient_id=ingredient_id,
            ingredient_name="flour",
            usda_food_description="Wheat flour, white, all-purpose, enriched",
            allergen_type="GLUTEN",
            presence_type="CONTAINS",
            confidence_score=Decimal("1.0"),
            source_notes=source_notes,
            data_source="USDA",
            profile_confidence=Decimal("1.0"),
        )

    @classmethod
    def flour_wheat(
        cls,
        ingredient_id: int = 1,
        source_notes: str = "Made from wheat",
    ) -> AllergenData:
        """Create flour with WHEAT allergen."""
        return cls.build(
            ingredient_id=ingredient_id,
            ingredient_name="flour",
            usda_food_description="Wheat flour, white, all-purpose, enriched",
            allergen_type="WHEAT",
            presence_type="CONTAINS",
            confidence_score=Decimal("1.0"),
            source_notes=source_notes,
            data_source="USDA",
            profile_confidence=Decimal("1.0"),
        )

    @classmethod
    def butter_milk(
        cls,
        ingredient_id: int = 2,
        source_notes: str = "Dairy product",
    ) -> AllergenData:
        """Create butter with MILK allergen."""
        return cls.build(
            ingredient_id=ingredient_id,
            ingredient_name="butter",
            usda_food_description="Butter, salted",
            allergen_type="MILK",
            presence_type="CONTAINS",
            confidence_score=Decimal("1.0"),
            source_notes=source_notes,
            data_source="USDA",
            profile_confidence=Decimal("1.0"),
        )

    @classmethod
    def eggs_eggs(
        cls,
        ingredient_id: int = 3,
        source_notes: str = "Contains eggs",
    ) -> AllergenData:
        """Create eggs with EGGS allergen."""
        return cls.build(
            ingredient_id=ingredient_id,
            ingredient_name="eggs",
            usda_food_description="Egg, whole, raw, fresh",
            allergen_type="EGGS",
            presence_type="CONTAINS",
            confidence_score=Decimal("1.0"),
            source_notes=source_notes,
            data_source="USDA",
            profile_confidence=Decimal("1.0"),
        )

    @classmethod
    def chicken_empty(cls, ingredient_id: int = 4) -> AllergenData:
        """Create chicken with no allergens (profile only)."""
        return cls.build(
            ingredient_id=ingredient_id,
            ingredient_name="chicken",
            usda_food_description="Chicken, broiler or fryers, breast, skinless",
            allergen_type="",
            presence_type="CONTAINS",
            confidence_score=Decimal("1.0"),
            source_notes=None,
            data_source="USDA",
            profile_confidence=Decimal("1.0"),
        )
