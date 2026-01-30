"""Unit tests for allergen schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.allergen import (
    AllergenDataSource,
    AllergenInfo,
    AllergenPresenceType,
    IngredientAllergenResponse,
    RecipeAllergenResponse,
)
from app.schemas.enums import Allergen


pytestmark = pytest.mark.unit


class TestAllergenPresenceType:
    """Tests for AllergenPresenceType enum."""

    def test_contains_value(self) -> None:
        """Should have CONTAINS value."""
        assert AllergenPresenceType.CONTAINS == "CONTAINS"

    def test_may_contain_value(self) -> None:
        """Should have MAY_CONTAIN value."""
        assert AllergenPresenceType.MAY_CONTAIN == "MAY_CONTAIN"

    def test_traces_value(self) -> None:
        """Should have TRACES value."""
        assert AllergenPresenceType.TRACES == "TRACES"


class TestAllergenDataSource:
    """Tests for AllergenDataSource enum."""

    def test_usda_value(self) -> None:
        """Should have USDA value."""
        assert AllergenDataSource.USDA == "USDA"

    def test_open_food_facts_value(self) -> None:
        """Should have OPEN_FOOD_FACTS value."""
        assert AllergenDataSource.OPEN_FOOD_FACTS == "OPEN_FOOD_FACTS"

    def test_llm_inferred_value(self) -> None:
        """Should have LLM_INFERRED value."""
        assert AllergenDataSource.LLM_INFERRED == "LLM_INFERRED"

    def test_manual_value(self) -> None:
        """Should have MANUAL value."""
        assert AllergenDataSource.MANUAL == "MANUAL"


class TestAllergenInfo:
    """Tests for AllergenInfo schema."""

    def test_minimal_creation(self) -> None:
        """Should create with just allergen field."""
        info = AllergenInfo(allergen=Allergen.GLUTEN)
        assert info.allergen == Allergen.GLUTEN
        assert info.presence_type == AllergenPresenceType.CONTAINS
        assert info.confidence_score is None
        assert info.source_notes is None

    def test_full_creation(self) -> None:
        """Should create with all fields."""
        info = AllergenInfo(
            allergen=Allergen.MILK,
            presence_type=AllergenPresenceType.MAY_CONTAIN,
            confidence_score=0.95,
            source_notes="From Open Food Facts",
        )
        assert info.allergen == Allergen.MILK
        assert info.presence_type == AllergenPresenceType.MAY_CONTAIN
        assert info.confidence_score == 0.95
        assert info.source_notes == "From Open Food Facts"

    def test_confidence_score_validation_min(self) -> None:
        """Should reject confidence score below 0."""
        with pytest.raises(ValidationError) as exc_info:
            AllergenInfo(allergen=Allergen.GLUTEN, confidence_score=-0.1)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_confidence_score_validation_max(self) -> None:
        """Should reject confidence score above 1."""
        with pytest.raises(ValidationError) as exc_info:
            AllergenInfo(allergen=Allergen.GLUTEN, confidence_score=1.1)
        assert "less than or equal to 1" in str(exc_info.value)

    def test_confidence_score_boundary_values(self) -> None:
        """Should accept boundary values 0 and 1."""
        info_min = AllergenInfo(allergen=Allergen.GLUTEN, confidence_score=0.0)
        info_max = AllergenInfo(allergen=Allergen.GLUTEN, confidence_score=1.0)
        assert info_min.confidence_score == 0.0
        assert info_max.confidence_score == 1.0


class TestIngredientAllergenResponse:
    """Tests for IngredientAllergenResponse schema."""

    def test_empty_creation(self) -> None:
        """Should create with defaults."""
        response = IngredientAllergenResponse()
        assert response.ingredient_id is None
        assert response.ingredient_name is None
        assert response.usda_food_description is None
        assert response.allergens == []
        assert response.data_source is None
        assert response.overall_confidence is None

    def test_full_creation(self) -> None:
        """Should create with all fields."""
        response = IngredientAllergenResponse(
            ingredient_id=1,
            ingredient_name="flour",
            usda_food_description="Wheat flour, white, all-purpose",
            allergens=[
                AllergenInfo(
                    allergen=Allergen.GLUTEN,
                    confidence_score=0.99,
                ),
                AllergenInfo(
                    allergen=Allergen.WHEAT,
                    confidence_score=0.99,
                ),
            ],
            data_source=AllergenDataSource.USDA,
            overall_confidence=0.99,
        )
        assert response.ingredient_id == 1
        assert response.ingredient_name == "flour"
        assert len(response.allergens) == 2
        assert response.data_source == AllergenDataSource.USDA

    def test_overall_confidence_validation(self) -> None:
        """Should validate overall_confidence range."""
        with pytest.raises(ValidationError):
            IngredientAllergenResponse(overall_confidence=1.5)

    def test_json_serialization(self) -> None:
        """Should serialize to JSON with camelCase keys."""
        response = IngredientAllergenResponse(
            ingredient_name="butter",
            allergens=[AllergenInfo(allergen=Allergen.MILK)],
            data_source=AllergenDataSource.USDA,
        )
        json_data = response.model_dump(mode="json")
        # Schema uses camelCase aliases for JSON serialization
        assert json_data["ingredientName"] == "butter"
        assert json_data["allergens"][0]["allergen"] == "MILK"
        assert json_data["dataSource"] == "USDA"


class TestRecipeAllergenResponse:
    """Tests for RecipeAllergenResponse schema."""

    def test_empty_creation(self) -> None:
        """Should create with defaults."""
        response = RecipeAllergenResponse()
        assert response.contains == []
        assert response.may_contain == []
        assert response.allergens == []
        assert response.ingredient_details is None
        assert response.missing_ingredients == []

    def test_full_creation(self) -> None:
        """Should create with all fields."""
        response = RecipeAllergenResponse(
            contains=[Allergen.GLUTEN, Allergen.EGGS],
            may_contain=[Allergen.TREE_NUTS],
            allergens=[
                AllergenInfo(allergen=Allergen.GLUTEN),
                AllergenInfo(allergen=Allergen.EGGS),
                AllergenInfo(
                    allergen=Allergen.TREE_NUTS,
                    presence_type=AllergenPresenceType.MAY_CONTAIN,
                ),
            ],
            ingredient_details={
                "flour": IngredientAllergenResponse(
                    ingredient_name="flour",
                    allergens=[AllergenInfo(allergen=Allergen.GLUTEN)],
                )
            },
            missing_ingredients=[103, 105],
        )
        assert Allergen.GLUTEN in response.contains
        assert Allergen.EGGS in response.contains
        assert Allergen.TREE_NUTS in response.may_contain
        assert len(response.allergens) == 3
        assert "flour" in response.ingredient_details
        assert response.missing_ingredients == [103, 105]

    def test_json_serialization(self) -> None:
        """Should serialize to JSON with camelCase keys."""
        response = RecipeAllergenResponse(
            contains=[Allergen.MILK],
            may_contain=[],
            allergens=[AllergenInfo(allergen=Allergen.MILK)],
        )
        json_data = response.model_dump(mode="json")
        # Schema uses camelCase aliases for JSON serialization
        assert json_data["contains"] == ["MILK"]
        assert json_data["mayContain"] == []
        assert json_data["allergens"][0]["allergen"] == "MILK"
