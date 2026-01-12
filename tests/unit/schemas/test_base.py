"""Tests for base schema configuration and behavior."""

from enum import StrEnum

import pytest
from pydantic import Field, ValidationError

from app.schemas.base import (
    APIRequest,
    APIResponse,
    DownstreamRequest,
    DownstreamResponse,
)


pytestmark = pytest.mark.unit


class TestCamelCaseSerialization:
    """Tests for snake_case to camelCase serialization."""

    def test_api_response_serializes_to_camel_case(self):
        """APIResponse should serialize snake_case fields to camelCase."""

        class TestResponse(APIResponse):
            user_name: str
            created_at: str
            is_active: bool

        response = TestResponse(
            user_name="john",
            created_at="2024-01-01",
            is_active=True,
        )
        data = response.model_dump()

        assert "userName" in data
        assert "createdAt" in data
        assert "isActive" in data
        assert "user_name" not in data

    def test_api_request_serializes_to_camel_case(self):
        """APIRequest should serialize snake_case fields to camelCase."""

        class TestRequest(APIRequest):
            first_name: str
            last_name: str

        request = TestRequest(first_name="John", last_name="Doe")
        data = request.model_dump()

        assert "firstName" in data
        assert "lastName" in data

    def test_accepts_camel_case_input(self):
        """Models should accept camelCase input via populate_by_name."""

        class TestResponse(APIResponse):
            user_name: str
            is_active: bool

        # Should accept camelCase
        response = TestResponse(userName="john", isActive=True)
        assert response.user_name == "john"
        assert response.is_active is True

    def test_accepts_snake_case_input(self):
        """Models should also accept snake_case input."""

        class TestResponse(APIResponse):
            user_name: str
            is_active: bool

        # Should accept snake_case
        response = TestResponse(user_name="john", is_active=True)
        assert response.user_name == "john"
        assert response.is_active is True

    def test_json_serialization_uses_camel_case(self):
        """JSON serialization should use camelCase."""

        class TestResponse(APIResponse):
            recipe_id: int
            cooking_time: int

        response = TestResponse(recipe_id=1, cooking_time=30)
        json_str = response.model_dump_json()

        assert "recipeId" in json_str
        assert "cookingTime" in json_str
        assert "recipe_id" not in json_str


class TestExtraFieldsBehavior:
    """Tests for extra fields handling in different schema types."""

    def test_api_request_ignores_extra_fields(self):
        """APIRequest should ignore unknown fields (lenient on incoming)."""

        class TestRequest(APIRequest):
            name: str

        # Should not raise, extra field ignored
        request = TestRequest(name="test", unknown_field="ignored")
        assert request.name == "test"
        assert not hasattr(request, "unknown_field")

    def test_api_response_forbids_extra_fields(self):
        """APIResponse should reject unknown fields (strict on outgoing)."""

        class TestResponse(APIResponse):
            name: str

        with pytest.raises(ValidationError) as exc_info:
            TestResponse(name="test", unknown_field="rejected")

        errors = exc_info.value.errors()
        assert any(err["type"] == "extra_forbidden" for err in errors)

    def test_downstream_request_forbids_extra_fields(self):
        """DownstreamRequest should reject unknown fields (strict on what we send)."""

        class TestRequest(DownstreamRequest):
            api_key: str

        with pytest.raises(ValidationError) as exc_info:
            TestRequest(api_key="key123", extra_param="rejected")

        errors = exc_info.value.errors()
        assert any(err["type"] == "extra_forbidden" for err in errors)

    def test_downstream_response_ignores_extra_fields(self):
        """DownstreamResponse should ignore unknown fields (lenient on what we receive)."""

        class TestResponse(DownstreamResponse):
            result: str

        # Should not raise, extra field from external service ignored
        response = TestResponse(result="ok", new_api_field="ignored")
        assert response.result == "ok"
        assert not hasattr(response, "new_api_field")


class TestValidationBehavior:
    """Tests for validation settings on base schemas."""

    def test_validates_on_assignment(self):
        """Models should validate when fields are assigned."""

        class TestResponse(APIResponse):
            count: int = Field(..., ge=0)

        response = TestResponse(count=5)

        with pytest.raises(ValidationError):
            response.count = -1

    def test_use_enum_values(self):
        """Enums should serialize as their values, not enum objects."""

        class Status(StrEnum):
            ACTIVE = "active"
            INACTIVE = "inactive"

        class TestResponse(APIResponse):
            status: Status

        response = TestResponse(status=Status.ACTIVE)
        data = response.model_dump()

        assert data["status"] == "active"
        assert not isinstance(data["status"], Status)


class TestInheritanceChain:
    """Tests to ensure config inheritance works correctly."""

    def test_nested_inheritance_preserves_config(self):
        """Subclasses of schema bases should preserve configuration."""

        class BaseResponse(APIResponse):
            base_field: str

        class ExtendedResponse(BaseResponse):
            extended_field: str
            nested_value: int

        response = ExtendedResponse(
            base_field="base",
            extended_field="extended",
            nested_value=42,
        )
        data = response.model_dump()

        # Should have camelCase
        assert "baseField" in data
        assert "extendedField" in data
        assert "nestedValue" in data

        # Should still forbid extra
        with pytest.raises(ValidationError):
            ExtendedResponse(
                base_field="base",
                extended_field="extended",
                nested_value=42,
                extra="not_allowed",
            )
