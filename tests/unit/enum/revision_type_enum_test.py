"""Unit tests for the RevisionTypeEnum."""

import pytest

from app.enums.revision_type_enum import RevisionTypeEnum


class TestRevisionTypeEnum:
    """Unit tests for the RevisionTypeEnum class."""

    @pytest.mark.unit
    def test_revision_type_enum_is_string_enum(self) -> None:
        """Test that RevisionTypeEnum values are strings."""
        # Act & Assert
        assert isinstance(RevisionTypeEnum.ADD, str)
        assert isinstance(RevisionTypeEnum.UPDATE, str)
        assert isinstance(RevisionTypeEnum.DELETE, str)

    @pytest.mark.unit
    def test_revision_type_enum_values(self) -> None:
        """Test that all revision type enum values are correct."""
        # Test all revision type values using a dictionary mapping
        expected_values = {
            RevisionTypeEnum.ADD: "ADD",
            RevisionTypeEnum.UPDATE: "UPDATE",
            RevisionTypeEnum.DELETE: "DELETE",
        }

        # Assert all values match expected strings
        for enum_val, expected_str in expected_values.items():
            assert enum_val == expected_str

    @pytest.mark.unit
    def test_revision_type_enum_membership(self) -> None:
        """Test that values are members of the enum."""
        # Act & Assert
        assert RevisionTypeEnum.ADD in RevisionTypeEnum
        assert RevisionTypeEnum.UPDATE in RevisionTypeEnum
        assert RevisionTypeEnum.DELETE in RevisionTypeEnum

    @pytest.mark.unit
    def test_revision_type_enum_iteration(self) -> None:
        """Test that we can iterate over all revision type values."""
        # Act
        all_types = list(RevisionTypeEnum)

        # Assert
        assert len(all_types) == 3
        assert RevisionTypeEnum.ADD in all_types
        assert RevisionTypeEnum.UPDATE in all_types
        assert RevisionTypeEnum.DELETE in all_types

    @pytest.mark.unit
    def test_revision_type_enum_count(self) -> None:
        """Test the total count of revision type enums."""
        # Act
        type_count = len(list(RevisionTypeEnum))

        # Assert
        assert type_count == 3

    @pytest.mark.unit
    def test_revision_type_enum_string_comparison(self) -> None:
        """Test that enum values can be compared with strings."""
        # Test equality comparisons
        equality_tests = {
            RevisionTypeEnum.ADD: "ADD",
            RevisionTypeEnum.UPDATE: "UPDATE",
            RevisionTypeEnum.DELETE: "DELETE",
        }

        for enum_val, expected_str in equality_tests.items():
            assert enum_val == expected_str

        # Test inequality with dynamic comparison
        test_cases = [
            (RevisionTypeEnum.ADD, "DELETE"),
            (RevisionTypeEnum.UPDATE, "ADD"),
        ]

        for enum_val, different_str in test_cases:
            assert enum_val != different_str

    @pytest.mark.unit
    def test_revision_type_enum_uniqueness(self) -> None:
        """Test that all revision type values are unique."""
        # Act
        all_values = [rev_type.value for rev_type in RevisionTypeEnum]

        # Assert
        assert len(all_values) == len(set(all_values))

    @pytest.mark.unit
    def test_revision_type_enum_covers_crud_operations(self) -> None:
        """Test that revision types cover the main CRUD operations."""
        # Act & Assert - Verify we have the essential CRUD operations
        assert RevisionTypeEnum.ADD in RevisionTypeEnum  # Create
        assert RevisionTypeEnum.UPDATE in RevisionTypeEnum  # Update
        assert RevisionTypeEnum.DELETE in RevisionTypeEnum  # Delete
        # Note: Read operations don't typically require revisions

        # Verify completeness for revision operations
        expected_types = {
            RevisionTypeEnum.ADD,
            RevisionTypeEnum.UPDATE,
            RevisionTypeEnum.DELETE,
        }
        actual_types = set(RevisionTypeEnum)
        assert actual_types == expected_types

    @pytest.mark.unit
    def test_revision_type_enum_can_be_used_in_sets(self) -> None:
        """Test that revision type enums can be used in sets."""
        # Act
        modification_types = {
            RevisionTypeEnum.ADD,
            RevisionTypeEnum.UPDATE,
        }
        destructive_types = {
            RevisionTypeEnum.DELETE,
        }

        # Assert
        assert len(modification_types) == 2
        assert len(destructive_types) == 1
        assert RevisionTypeEnum.ADD in modification_types
        assert RevisionTypeEnum.UPDATE in modification_types
        assert RevisionTypeEnum.DELETE in destructive_types
        assert RevisionTypeEnum.DELETE not in modification_types

    @pytest.mark.unit
    def test_revision_type_enum_serializable_to_string(self) -> None:
        """Test that revision type enums are serializable to strings."""
        # Act & Assert - Test the value attribute for string representation
        assert RevisionTypeEnum.ADD.value == "ADD"
        assert RevisionTypeEnum.UPDATE.value == "UPDATE"
        assert RevisionTypeEnum.DELETE.value == "DELETE"

    @pytest.mark.unit
    def test_revision_type_enum_name_attribute(self) -> None:
        """Test that revision type enums have correct name attributes."""
        # Act & Assert
        assert RevisionTypeEnum.ADD.name == "ADD"
        assert RevisionTypeEnum.UPDATE.name == "UPDATE"
        assert RevisionTypeEnum.DELETE.name == "DELETE"

    @pytest.mark.unit
    def test_revision_type_enum_value_attribute(self) -> None:
        """Test that revision type enums have correct value attributes."""
        # Act & Assert
        assert RevisionTypeEnum.ADD.value == "ADD"
        assert RevisionTypeEnum.UPDATE.value == "UPDATE"
        assert RevisionTypeEnum.DELETE.value == "DELETE"
