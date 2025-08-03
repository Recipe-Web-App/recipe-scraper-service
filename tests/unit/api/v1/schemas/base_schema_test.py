"""Unit tests for BaseSchema and its Pydantic config behavior."""

from enum import Enum

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.base_schema import BaseSchema


class Color(Enum):
    """Example enum for testing enum serialization in BaseSchema."""

    RED = "red"
    BLUE = "blue"


class ExampleSchema(BaseSchema):
    """Example schema inheriting from BaseSchema for testing purposes."""

    some_field: str
    color: str


@pytest.mark.unit
def test_camelcase_serialization() -> None:
    """Test that snake_case fields serialize to camelCase and enums use values."""
    obj = ExampleSchema(some_field="foo", color=Color.RED)
    data = obj.model_dump(by_alias=True)
    assert "someField" in data
    assert data["someField"] == "foo"
    assert data["color"] == "red"


@pytest.mark.unit
def test_deserialize_snake_and_camel() -> None:
    """Test that both snake_case and camelCase are accepted during deserialization."""
    # Direct instantiation with Enum instance
    obj1 = ExampleSchema(some_field="foo", color=Color.BLUE)
    assert obj1.some_field == "foo"
    assert obj1.color == "blue"
    # model_validate with camelCase
    obj2 = ExampleSchema.model_validate({"someField": "bar", "color": "red"})
    assert obj2.some_field == "bar"
    assert obj2.color == "red"
    # model_validate with snake_case
    obj3 = ExampleSchema.model_validate({"some_field": "baz", "color": "blue"})
    assert obj3.some_field == "baz"
    assert obj3.color == "blue"


@pytest.mark.unit
def test_forbid_extra_fields() -> None:
    """Test that extra fields are forbidden and raise a ValidationError."""
    with pytest.raises(ValidationError):
        ExampleSchema(some_field="foo", color="red", extra_field=123)  # type: ignore[call-arg]


@pytest.mark.unit
def test_strip_whitespace() -> None:
    """Test that leading/trailing whitespace is stripped from string fields."""
    obj = ExampleSchema(some_field="  foo  ", color="red")
    assert obj.some_field == "foo"
