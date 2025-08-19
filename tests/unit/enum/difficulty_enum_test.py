"""Unit tests for the DifficultyLevelEnum."""

import pytest

from app.enums.difficulty_level_enum import DifficultyLevelEnum


class TestDifficultyLevelEnum:
    """Unit tests for the DifficultyLevelEnum class."""

    @pytest.mark.unit
    def test_difficulty_level_enum_is_string_enum(self) -> None:
        """Test that DifficultyLevelEnum values are strings."""
        # Act & Assert
        assert isinstance(DifficultyLevelEnum.BEGINNER, str)
        assert isinstance(DifficultyLevelEnum.EASY, str)
        assert isinstance(DifficultyLevelEnum.EXPERT, str)

    @pytest.mark.unit
    def test_difficulty_level_enum_values(self) -> None:
        """Test that all difficulty level enum values are correct."""
        # Act
        values = {
            DifficultyLevelEnum.BEGINNER: "BEGINNER",
            DifficultyLevelEnum.EASY: "EASY",
            DifficultyLevelEnum.MEDIUM: "MEDIUM",
            DifficultyLevelEnum.HARD: "HARD",
            DifficultyLevelEnum.EXPERT: "EXPERT",
        }

        # Assert
        for enum_val, expected_str in values.items():
            assert enum_val == expected_str

    @pytest.mark.unit
    def test_difficulty_level_enum_membership(self) -> None:
        """Test that values are members of the enum."""
        # Act & Assert
        assert DifficultyLevelEnum.BEGINNER in DifficultyLevelEnum
        assert DifficultyLevelEnum.EASY in DifficultyLevelEnum
        assert DifficultyLevelEnum.MEDIUM in DifficultyLevelEnum
        assert DifficultyLevelEnum.HARD in DifficultyLevelEnum
        assert DifficultyLevelEnum.EXPERT in DifficultyLevelEnum

    @pytest.mark.unit
    def test_difficulty_level_enum_iteration(self) -> None:
        """Test that we can iterate over all difficulty level values."""
        # Act
        all_difficulty_levels = list(DifficultyLevelEnum)

        # Assert
        assert len(all_difficulty_levels) == 5
        assert DifficultyLevelEnum.BEGINNER in all_difficulty_levels
        assert DifficultyLevelEnum.EASY in all_difficulty_levels
        assert DifficultyLevelEnum.MEDIUM in all_difficulty_levels
        assert DifficultyLevelEnum.HARD in all_difficulty_levels
        assert DifficultyLevelEnum.EXPERT in all_difficulty_levels

    @pytest.mark.unit
    def test_difficulty_level_enum_count(self) -> None:
        """Test the total count of difficulty level enums."""
        # Act
        difficulty_count = len(list(DifficultyLevelEnum))

        # Assert
        assert difficulty_count == 5

    @pytest.mark.unit
    def test_difficulty_level_enum_string_comparison(self) -> None:
        """Test that enum values can be compared with strings."""
        # Test equality comparisons
        equality_tests = {
            DifficultyLevelEnum.BEGINNER: "BEGINNER",
            DifficultyLevelEnum.EASY: "EASY",
            DifficultyLevelEnum.MEDIUM: "MEDIUM",
        }

        for enum_val, expected_str in equality_tests.items():
            assert enum_val == expected_str

        # Test inequality comparisons
        inequality_tests = [
            (DifficultyLevelEnum.BEGINNER, "EXPERT"),
            (DifficultyLevelEnum.HARD, "EASY"),
        ]

        for enum_val, different_str in inequality_tests:
            assert enum_val != different_str

    @pytest.mark.unit
    def test_difficulty_level_enum_uniqueness(self) -> None:
        """Test that all difficulty level values are unique."""
        # Act
        all_values = [level.value for level in DifficultyLevelEnum]

        # Assert
        assert len(all_values) == len(set(all_values))

    @pytest.mark.unit
    def test_difficulty_level_ordering_concept(self) -> None:
        """Test that difficulty levels represent a logical progression."""
        # Act - Get all difficulty levels
        levels = list(DifficultyLevelEnum)

        # Assert - Verify we have the expected progression levels
        expected_levels = {
            DifficultyLevelEnum.BEGINNER,
            DifficultyLevelEnum.EASY,
            DifficultyLevelEnum.MEDIUM,
            DifficultyLevelEnum.HARD,
            DifficultyLevelEnum.EXPERT,
        }
        assert set(levels) == expected_levels

    @pytest.mark.unit
    def test_difficulty_level_enum_can_be_used_in_sets(self) -> None:
        """Test that difficulty level enums can be used in sets."""
        # Act
        easy_levels = {
            DifficultyLevelEnum.BEGINNER,
            DifficultyLevelEnum.EASY,
        }
        hard_levels = {
            DifficultyLevelEnum.HARD,
            DifficultyLevelEnum.EXPERT,
        }

        # Assert
        assert len(easy_levels) == 2
        assert len(hard_levels) == 2
        assert DifficultyLevelEnum.BEGINNER in easy_levels
        assert DifficultyLevelEnum.EXPERT in hard_levels
        assert DifficultyLevelEnum.MEDIUM not in easy_levels
        assert DifficultyLevelEnum.MEDIUM not in hard_levels

    @pytest.mark.unit
    def test_difficulty_level_enum_serializable_to_string(self) -> None:
        """Test that difficulty level enums are serializable to strings."""
        # Act & Assert - Test the value attribute for string representation
        assert DifficultyLevelEnum.BEGINNER.value == "BEGINNER"
        assert DifficultyLevelEnum.EASY.value == "EASY"
        assert DifficultyLevelEnum.MEDIUM.value == "MEDIUM"
        assert DifficultyLevelEnum.HARD.value == "HARD"
        assert DifficultyLevelEnum.EXPERT.value == "EXPERT"

    @pytest.mark.unit
    def test_difficulty_level_enum_name_attribute(self) -> None:
        """Test that difficulty level enums have correct name attributes."""
        # Act & Assert
        assert DifficultyLevelEnum.BEGINNER.name == "BEGINNER"
        assert DifficultyLevelEnum.EASY.name == "EASY"
        assert DifficultyLevelEnum.MEDIUM.name == "MEDIUM"
        assert DifficultyLevelEnum.HARD.name == "HARD"
        assert DifficultyLevelEnum.EXPERT.name == "EXPERT"

    @pytest.mark.unit
    def test_difficulty_level_enum_value_attribute(self) -> None:
        """Test that difficulty level enums have correct value attributes."""
        # Act & Assert
        assert DifficultyLevelEnum.BEGINNER.value == "BEGINNER"
        assert DifficultyLevelEnum.EASY.value == "EASY"
        assert DifficultyLevelEnum.MEDIUM.value == "MEDIUM"
        assert DifficultyLevelEnum.HARD.value == "HARD"
        assert DifficultyLevelEnum.EXPERT.value == "EXPERT"

    @pytest.mark.unit
    def test_difficulty_level_ranges(self) -> None:
        """Test grouping difficulty levels into ranges."""
        # Act
        beginner_range = {DifficultyLevelEnum.BEGINNER, DifficultyLevelEnum.EASY}
        intermediate_range = {DifficultyLevelEnum.MEDIUM}
        advanced_range = {DifficultyLevelEnum.HARD, DifficultyLevelEnum.EXPERT}

        # Assert
        assert len(beginner_range) == 2
        assert len(intermediate_range) == 1
        assert len(advanced_range) == 2

        # Verify no overlap
        all_ranges = beginner_range | intermediate_range | advanced_range
        assert len(all_ranges) == 5
        assert all_ranges == set(DifficultyLevelEnum)
