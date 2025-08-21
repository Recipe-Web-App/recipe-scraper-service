"""Unit tests for the BaseDatabaseModel class."""

import enum
import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base_database_model import BaseDatabaseModel


class SampleEnum(enum.Enum):
    """Sample enum for serialization testing."""

    VALUE_ONE = "value_one"
    VALUE_TWO = "value_two"


class SampleModel(BaseDatabaseModel):
    """Test model for testing BaseDatabaseModel functionality."""

    __tablename__ = "test_model"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))


class TestBaseDatabaseModel:
    """Test cases for BaseDatabaseModel."""

    @pytest.mark.unit
    def test_repr_calls_to_json(self) -> None:
        """Test that __repr__ calls _to_json method."""
        model = SampleModel(id=1, name="test")
        result = repr(model)

        # Should return JSON representation
        assert '"id": 1' in result
        assert '"name": "test"' in result

    @pytest.mark.unit
    def test_str_calls_to_json(self) -> None:
        """Test that __str__ calls _to_json method."""
        model = SampleModel(id=1, name="test")
        result = str(model)

        # Should return JSON representation
        assert '"id": 1' in result
        assert '"name": "test"' in result

    @pytest.mark.unit
    def test_to_json_serializes_model(self) -> None:
        """Test that _to_json properly serializes a model."""
        model = SampleModel(id=1, name="test")
        result = model._to_json()

        parsed = json.loads(result)
        assert parsed["id"] == 1
        assert parsed["name"] == "test"

    @pytest.mark.unit
    def test_serialize_basic_object(self) -> None:
        """Test serialization of basic objects."""
        result = BaseDatabaseModel._serialize("test_string")
        assert result == "test_string"

        result = BaseDatabaseModel._serialize(123)
        assert result == 123

        result = BaseDatabaseModel._serialize(12.34)
        assert result == 12.34

    @pytest.mark.unit
    def test_serialize_list(self) -> None:
        """Test serialization of lists."""
        test_list = [1, "test", 3.14]
        result = BaseDatabaseModel._serialize(test_list)
        assert result == [1, "test", 3.14]

    @pytest.mark.unit
    def test_serialize_enum(self) -> None:
        """Test serialization of enum values."""
        test_enum = SampleEnum.VALUE_ONE
        result = BaseDatabaseModel._serialize(test_enum)
        assert result == "value_one"

    @pytest.mark.unit
    def test_serialize_object_with_dict(self) -> None:
        """Test serialization of objects with __dict__."""

        class TestObject:
            def __init__(self) -> None:
                self.public_attr = "public"
                self._private_attr = "private"
                self.__dunder_attr = "dunder"
                self._sa_instance_state = "sqlalchemy_state"

        obj = TestObject()
        result = BaseDatabaseModel._serialize(obj)

        assert isinstance(result, dict)
        assert result["public_attr"] == "public"
        assert result["_private_attr"] == "private"
        # Should exclude SQLAlchemy state and dunder attributes
        assert "_sa_instance_state" not in result
        assert "__dunder_attr" not in result

    @pytest.mark.unit
    def test_serialize_datetime_like_object(self, mock_datetime: datetime) -> None:
        """Test serialization of objects with isoformat method."""
        result = BaseDatabaseModel._serialize(mock_datetime)
        assert result == mock_datetime.isoformat()

    @pytest.mark.unit
    def test_serialize_circular_reference_prevention(self) -> None:
        """Test that circular references are handled properly."""
        obj1 = SampleModel(id=1, name="obj1")
        obj2 = SampleModel(id=2, name="obj2")

        # Create circular reference by setting each as an attribute of the other
        obj1.circular_ref = obj2  # type: ignore[attr-defined]
        obj2.circular_ref = obj1  # type: ignore[attr-defined]

        result = BaseDatabaseModel._serialize(obj1)

        # Should contain the serialized representation and not cause infinite recursion
        assert isinstance(result, dict)
        assert result["id"] == 1
        assert result["name"] == "obj1"
        # The circular reference should be represented as a string or dict
        assert isinstance(result["circular_ref"], str | dict)
        assert "circular_ref" in str(result["circular_ref"])

    @pytest.mark.unit
    def test_get_circular_ref_repr_with_tablename(self) -> None:
        """Test _get_circular_ref_repr with object having __tablename__."""
        model = SampleModel(id=123, name="test")
        result = BaseDatabaseModel._get_circular_ref_repr(model)

        assert "SampleModel" in result
        assert "test_model" in result
        assert "123" in result or "unknown" in result

    @pytest.mark.unit
    def test_get_circular_ref_repr_without_tablename(self) -> None:
        """Test _get_circular_ref_repr with object without __tablename__."""

        class SimpleObject:
            pass

        obj = SimpleObject()
        result = BaseDatabaseModel._get_circular_ref_repr(obj)

        assert "circular_ref:SimpleObject" in result

    @pytest.mark.unit
    def test_serialize_visited_set_management(self) -> None:
        """Test that visited set is properly managed during serialization."""
        # Create a model with some attributes
        model = SampleModel(id=1, name="test")

        # Add some nested attributes
        model.nested_dict = {"key": "value"}  # type: ignore[attr-defined]
        model.nested_list = [1, 2, 3]  # type: ignore[attr-defined]

        result = BaseDatabaseModel._serialize(model)

        # Should successfully serialize without issues
        assert isinstance(result, dict)
        assert result["id"] == 1
        assert result["name"] == "test"
        assert result["nested_dict"] == {"key": "value"}
        assert result["nested_list"] == [1, 2, 3]

    @pytest.mark.unit
    def test_serialize_with_none_values(self) -> None:
        """Test serialization handles None values correctly."""
        model = SampleModel(id=1, name="test")
        model.none_value = None  # type: ignore[attr-defined]

        result = BaseDatabaseModel._serialize(model)

        assert isinstance(result, dict)
        assert result["none_value"] is None

    @pytest.mark.unit
    def test_serialize_nested_objects(self) -> None:
        """Test serialization of nested objects."""

        class NestedObject:
            def __init__(self) -> None:
                self.nested_attr = "nested_value"

        model = SampleModel(id=1, name="test")
        model.nested_obj = NestedObject()  # type: ignore[attr-defined]

        result = BaseDatabaseModel._serialize(model)

        assert isinstance(result, dict)
        assert isinstance(result["nested_obj"], dict)
        assert result["nested_obj"]["nested_attr"] == "nested_value"

    @pytest.mark.unit
    def test_serialize_complex_types(self, mock_user_id: UUID) -> None:
        """Test serialization of complex types like Decimal and UUID."""
        test_decimal = Decimal("123.45")

        decimal_result = BaseDatabaseModel._serialize(test_decimal)
        uuid_result = BaseDatabaseModel._serialize(mock_user_id)

        # These should be serialized as is (no isoformat method)
        assert isinstance(decimal_result, Decimal)
        assert isinstance(uuid_result, UUID)

    @pytest.mark.unit
    def test_to_json_with_complex_model(self, mock_datetime: datetime) -> None:
        """Test _to_json with a complex model containing various data types."""
        model = SampleModel(id=1, name="complex_test")
        model.enum_value = SampleEnum.VALUE_TWO  # type: ignore[attr-defined]
        model.list_value = [1, "test", SampleEnum.VALUE_ONE]  # type: ignore[attr-defined]
        model.decimal_value = Decimal("99.99")  # type: ignore[attr-defined]
        model.datetime_value = mock_datetime  # type: ignore[attr-defined]

        json_str = model._to_json()
        parsed = json.loads(json_str)

        assert parsed["id"] == 1
        assert parsed["name"] == "complex_test"
        assert parsed["enum_value"] == "value_two"
        assert parsed["list_value"] == [1, "test", "value_one"]
        # Decimal and datetime should be converted to string by json.dumps default=str
        assert isinstance(parsed["decimal_value"], str)
        assert isinstance(parsed["datetime_value"], str)
