"""Unit tests for the SpoonacularSubstitutesResponse schema and its logic."""

import pytest

from app.api.v1.schemas.downstream.spoonacular.substitute_item import (
    SpoonacularSubstituteItem,
)
from app.api.v1.schemas.downstream.spoonacular.substitutes_response import (
    SpoonacularSubstitutesResponse,
)

NAME = "Mock Substitute Name"
SUBSTITUTE = "Mock Substitute"
DESCRIPTION = "Mock description."

SUBSTITUTE_ITEM_DICT = {
    "name": NAME,
    "substitute": SUBSTITUTE,
    "description": DESCRIPTION,
}

SUBSTITUTE_ITEM_OBJ = SpoonacularSubstituteItem.model_validate(SUBSTITUTE_ITEM_DICT)

SUBSTITUTES = [SUBSTITUTE_ITEM_OBJ]

_similar_field_list = list(SpoonacularSubstitutesResponse.model_fields.keys())


@pytest.mark.unit
def test_substitutes_response_instantiation() -> None:
    """Test SpoonacularSubstitutesResponse can be instantiated with all fields."""
    # Arrange
    substitutes = [SUBSTITUTE_ITEM_DICT]  # Pass as dict, not model instance

    # Act
    resp = SpoonacularSubstitutesResponse(substitutes=substitutes)

    # Assert
    assert resp.substitutes == [SpoonacularSubstituteItem(**SUBSTITUTE_ITEM_DICT)]


@pytest.mark.unit
def test_substitutes_response_model_copy() -> None:
    """Test model_copy for SpoonacularSubstitutesResponse object."""
    # Arrange
    resp = SpoonacularSubstitutesResponse(substitutes=SUBSTITUTES)

    # Act
    resp_copy = resp.model_copy()

    # Assert
    assert resp == resp_copy
    assert resp is not resp_copy
    for field in _similar_field_list:
        assert getattr(resp, field) == getattr(resp_copy, field)


@pytest.mark.unit
def test_substitutes_response_equality() -> None:
    """Test equality for SpoonacularSubstitutesResponse objects with same data."""
    # Arrange
    kwargs1 = {"substitutes": [SUBSTITUTE_ITEM_DICT]}
    kwargs2: dict[str, list[dict[str, str]]] = {"substitutes": []}

    # Act
    r1 = SpoonacularSubstitutesResponse(**kwargs1)
    r2 = SpoonacularSubstitutesResponse(**kwargs1)
    r3 = SpoonacularSubstitutesResponse(**kwargs2)

    # Assert
    assert r1 == r2
    assert r1 != r3  # Now r1 has one item, r3 has none


@pytest.mark.unit
def test_substitutes_response_serialization() -> None:
    """Test that model_dump produces a serializable dict with all fields."""
    # Arrange
    resp = SpoonacularSubstitutesResponse(substitutes=SUBSTITUTES)

    # Act
    data = resp.model_dump()

    # Assert
    assert isinstance(data, dict)
    for field in _similar_field_list:
        if field == "substitutes":
            assert data[field] == [
                s.model_dump() if hasattr(s, "model_dump") else s
                for s in resp.substitutes
            ]
        else:
            assert data[field] == getattr(resp, field)


@pytest.mark.unit
def test_substitutes_response_deserialization() -> None:
    """Test model_validate reconstructs a SpoonacularSubstitutesResponse from dict.

    This test uses a field list and for-loop for field-by-field comparison.
    """
    # Arrange
    data = {"substitutes": [SUBSTITUTE_ITEM_DICT]}

    # Act
    resp = SpoonacularSubstitutesResponse.model_validate(data)

    # Assert
    assert isinstance(resp, SpoonacularSubstitutesResponse)
    for field in _similar_field_list:
        if field == "substitutes":
            assert resp.substitutes == [SUBSTITUTE_ITEM_OBJ]
        elif field in data:
            assert getattr(resp, field) == data[field]


@pytest.mark.unit
def test_substitutes_response_default_values() -> None:
    """Test SpoonacularSubstitutesResponse can be instantiated with default values.

    Only substitutes is required; it should default to [].
    """
    # Arrange and Act
    resp = SpoonacularSubstitutesResponse()

    # Assert
    assert resp.substitutes == []


@pytest.mark.unit
def test_substitutes_response_constraints() -> None:
    """Test schema constraints and required fields."""
    # Arrange and Act and Assert
    resp = SpoonacularSubstitutesResponse(substitutes="not-a-list")
    assert resp.substitutes == []
    resp = SpoonacularSubstitutesResponse(substitutes=[{"id": None}])
    assert resp.substitutes == []
    # Extra fields are ignored due to extra="ignore"
    resp = SpoonacularSubstitutesResponse(
        substitutes=[],
        extra_field=123,
    )
    assert hasattr(resp, "substitutes")
    assert not hasattr(resp, "extra_field")


@pytest.mark.unit
def test_substitutes_response_edge_cases() -> None:
    """Test substitutes field edge cases: None, not a list, invalid, or empty."""
    # Arrange and Act and Assert
    resp = SpoonacularSubstitutesResponse(substitutes=None)
    assert resp.substitutes == []
    resp = SpoonacularSubstitutesResponse(substitutes=[])
    assert resp.substitutes == []
    # Valid string and valid object are kept.
    # Invalid/empty/whitespace/invalid dicts are pruned.
    valid_str = "Valid Substitute"
    whitespace_str = "   "
    valid_dict = {"name": "Another Substitute"}
    resp = SpoonacularSubstitutesResponse(
        substitutes=[
            SUBSTITUTE_ITEM_DICT,  # pass as dict, not model instance
            valid_str,
            whitespace_str,
            123,
            valid_dict,
            None,
        ],
    )
    # The schema keeps valid strings and valid dicts (converted to model instances).
    # Order may differ, so check for presence and count.
    expected_substitute_count = 3
    assert valid_str in resp.substitutes
    assert SpoonacularSubstituteItem(name="Another Substitute") in resp.substitutes
    assert SpoonacularSubstituteItem(**SUBSTITUTE_ITEM_DICT) in resp.substitutes
    assert len(resp.substitutes) == expected_substitute_count
