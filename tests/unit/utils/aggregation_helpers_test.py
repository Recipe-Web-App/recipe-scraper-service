"""Unit tests for aggregation helper functions."""

from decimal import Decimal

import pytest

from app.utils.aggregation_helpers import (
    combine_nutriscore_grades_optional,
    combine_string_optional,
    sum_decimal_optional,
    sum_int_optional,
    sum_list_optional,
)


class TestCombineStringOptional:
    """Unit tests for the combine_string_optional function."""

    @pytest.mark.unit
    def test_combine_string_optional_first_non_none(self) -> None:
        """Test that the first non-None string is returned."""
        # Arrange
        a = "first"
        b = "second"

        # Act
        result = combine_string_optional(a, b)

        # Assert
        assert result == "first"

    @pytest.mark.unit
    def test_combine_string_optional_second_when_first_none(self) -> None:
        """Test that the second string is returned when first is None."""
        # Arrange
        a = None
        b = "second"

        # Act
        result = combine_string_optional(a, b)

        # Assert
        assert result == "second"

    @pytest.mark.unit
    def test_combine_string_optional_both_none(self) -> None:
        """Test that None is returned when both strings are None."""
        # Arrange
        a = None
        b = None

        # Act
        result = combine_string_optional(a, b)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_combine_string_optional_first_empty_string(self) -> None:
        """Test behavior when first string is empty."""
        # Arrange
        a = ""
        b = "second"

        # Act
        result = combine_string_optional(a, b)

        # Assert
        # Empty string is falsy, so second should be returned
        assert result == "second"

    @pytest.mark.unit
    def test_combine_string_optional_second_empty_string(self) -> None:
        """Test behavior when second string is empty."""
        # Arrange
        a = "first"
        b = ""

        # Act
        result = combine_string_optional(a, b)

        # Assert
        assert result == "first"

    @pytest.mark.unit
    def test_combine_string_optional_both_empty_strings(self) -> None:
        """Test behavior when both strings are empty."""
        # Arrange
        a = ""
        b = ""

        # Act
        result = combine_string_optional(a, b)

        # Assert
        # Both are falsy, so None should be returned
        assert result == ""


class TestCombineNutriscoreGradesOptional:
    """Unit tests for the combine_nutriscore_grades_optional function."""

    @pytest.mark.unit
    def test_combine_nutriscore_grades_both_none(self) -> None:
        """Test that None is returned when both grades are None."""
        # Arrange
        grade_a = None
        grade_b = None

        # Act
        result = combine_nutriscore_grades_optional(grade_a, grade_b)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_combine_nutriscore_grades_first_none(self) -> None:
        """Test that second grade is returned when first is None."""
        # Arrange
        grade_a = None
        grade_b = "B"

        # Act
        result = combine_nutriscore_grades_optional(grade_a, grade_b)

        # Assert
        assert result == "B"

    @pytest.mark.unit
    def test_combine_nutriscore_grades_second_none(self) -> None:
        """Test that first grade is returned when second is None."""
        # Arrange
        grade_a = "A"
        grade_b = None

        # Act
        result = combine_nutriscore_grades_optional(grade_a, grade_b)

        # Assert
        assert result == "A"

    @pytest.mark.unit
    def test_combine_nutriscore_grades_worse_grade_returned(self) -> None:
        """Test that the worse (higher) grade is returned."""
        # Arrange & Act & Assert
        test_cases = [
            ("A", "B", "B"),  # B is worse than A
            ("B", "A", "B"),  # B is worse than A
            ("A", "E", "E"),  # E is worse than A
            ("C", "D", "D"),  # D is worse than C
            ("E", "A", "E"),  # E is worse than A
        ]

        for grade_a, grade_b, expected in test_cases:
            result = combine_nutriscore_grades_optional(grade_a, grade_b)
            assert result == expected

    @pytest.mark.unit
    def test_combine_nutriscore_grades_same_grade(self) -> None:
        """Test behavior when both grades are the same."""
        # Arrange
        grade_a = "C"
        grade_b = "C"

        # Act
        result = combine_nutriscore_grades_optional(grade_a, grade_b)

        # Assert
        assert result == "C"

    @pytest.mark.unit
    def test_combine_nutriscore_grades_case_insensitive(self) -> None:
        """Test that grades are handled case-insensitively."""
        # Arrange & Act & Assert
        test_cases = [
            ("a", "b", "B"),  # lowercase inputs, uppercase output
            ("A", "b", "B"),  # mixed case
            ("c", "D", "D"),  # mixed case
        ]

        for grade_a, grade_b, expected in test_cases:
            result = combine_nutriscore_grades_optional(grade_a, grade_b)
            assert result == expected

    @pytest.mark.unit
    def test_combine_nutriscore_grades_invalid_grade(self) -> None:
        """Test behavior with invalid grades (defaults to E)."""
        # Arrange
        grade_a = "X"  # Invalid grade
        grade_b = "A"

        # Act
        result = combine_nutriscore_grades_optional(grade_a, grade_b)

        # Assert
        # Invalid grade should default to worst (E), so X should be returned
        assert result == "X"

    @pytest.mark.unit
    def test_combine_nutriscore_grades_both_invalid(self) -> None:
        """Test behavior when both grades are invalid."""
        # Arrange
        grade_a = "X"
        grade_b = "Y"

        # Act
        result = combine_nutriscore_grades_optional(grade_a, grade_b)

        # Assert
        # Both invalid, first should be returned as they have same value (5)
        assert result == "X"


class TestSumDecimalOptional:
    """Unit tests for the sum_decimal_optional function."""

    @pytest.mark.unit
    def test_sum_decimal_optional_both_none(self) -> None:
        """Test that None is returned when both decimals are None."""
        # Arrange
        a = None
        b = None

        # Act
        result = sum_decimal_optional(a, b)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_sum_decimal_optional_first_none(self) -> None:
        """Test sum when first decimal is None."""
        # Arrange
        a = None
        b = Decimal("5.5")

        # Act
        result = sum_decimal_optional(a, b)

        # Assert
        assert result == Decimal("5.500")

    @pytest.mark.unit
    def test_sum_decimal_optional_second_none(self) -> None:
        """Test sum when second decimal is None."""
        # Arrange
        a = Decimal("3.2")
        b = None

        # Act
        result = sum_decimal_optional(a, b)

        # Assert
        assert result == Decimal("3.200")

    @pytest.mark.unit
    def test_sum_decimal_optional_both_values(self) -> None:
        """Test sum when both decimals have values."""
        # Arrange
        a = Decimal("1.5")
        b = Decimal("2.75")

        # Act
        result = sum_decimal_optional(a, b)

        # Assert
        assert result == Decimal("4.250")

    @pytest.mark.unit
    def test_sum_decimal_optional_custom_precision(self) -> None:
        """Test sum with custom precision."""
        # Arrange
        a = Decimal("1.23456")
        b = Decimal("2.76543")
        precision = "0.01"  # 2 decimal places

        # Act
        result = sum_decimal_optional(a, b, precision)

        # Assert
        assert result == Decimal("4.00")

    @pytest.mark.unit
    def test_sum_decimal_optional_zero_precision(self) -> None:
        """Test sum with zero decimal places precision."""
        # Arrange
        a = Decimal("1.7")
        b = Decimal("2.3")
        precision = "1"  # No decimal places

        # Act
        result = sum_decimal_optional(a, b, precision)

        # Assert
        assert result == Decimal("4")

    @pytest.mark.unit
    def test_sum_decimal_optional_high_precision(self) -> None:
        """Test sum with high precision."""
        # Arrange
        a = Decimal("1.123456789")
        b = Decimal("2.987654321")
        precision = "0.000001"  # 6 decimal places

        # Act
        result = sum_decimal_optional(a, b, precision)

        # Assert
        assert result == Decimal("4.111111")

    @pytest.mark.unit
    def test_sum_decimal_optional_negative_values(self) -> None:
        """Test sum with negative decimal values."""
        # Arrange
        a = Decimal("-1.5")
        b = Decimal("3.2")

        # Act
        result = sum_decimal_optional(a, b)

        # Assert
        assert result == Decimal("1.700")


class TestSumIntOptional:
    """Unit tests for the sum_int_optional function."""

    @pytest.mark.unit
    def test_sum_int_optional_both_none(self) -> None:
        """Test that None is returned when both integers are None."""
        # Arrange
        a = None
        b = None

        # Act
        result = sum_int_optional(a, b)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_sum_int_optional_first_none(self) -> None:
        """Test sum when first integer is None."""
        # Arrange
        a = None
        b = 5

        # Act
        result = sum_int_optional(a, b)

        # Assert
        assert result == 5

    @pytest.mark.unit
    def test_sum_int_optional_second_none(self) -> None:
        """Test sum when second integer is None."""
        # Arrange
        a = 3
        b = None

        # Act
        result = sum_int_optional(a, b)

        # Assert
        assert result == 3

    @pytest.mark.unit
    def test_sum_int_optional_both_values(self) -> None:
        """Test sum when both integers have values."""
        # Arrange
        a = 10
        b = 25

        # Act
        result = sum_int_optional(a, b)

        # Assert
        assert result == 35

    @pytest.mark.unit
    def test_sum_int_optional_zero_values(self) -> None:
        """Test sum with zero values."""
        # Arrange
        a = 0
        b = 0

        # Act
        result = sum_int_optional(a, b)

        # Assert
        assert result == 0

    @pytest.mark.unit
    def test_sum_int_optional_negative_values(self) -> None:
        """Test sum with negative integers."""
        # Arrange
        a = -5
        b = 3

        # Act
        result = sum_int_optional(a, b)

        # Assert
        assert result == -2

    @pytest.mark.unit
    def test_sum_int_optional_large_values(self) -> None:
        """Test sum with large integer values."""
        # Arrange
        a = 1000000
        b = 2000000

        # Act
        result = sum_int_optional(a, b)

        # Assert
        assert result == 3000000


class TestSumListOptional:
    """Unit tests for the sum_list_optional function."""

    @pytest.mark.unit
    def test_sum_list_optional_both_none(self) -> None:
        """Test that None is returned when both lists are None."""
        # Arrange
        a = None
        b = None

        # Act
        result = sum_list_optional(a, b)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_sum_list_optional_first_none(self) -> None:
        """Test combination when first list is None."""
        # Arrange
        a = None
        b = [1, 2, 3]

        # Act
        result = sum_list_optional(a, b)

        # Assert
        assert result == [1, 2, 3]

    @pytest.mark.unit
    def test_sum_list_optional_second_none(self) -> None:
        """Test combination when second list is None."""
        # Arrange
        a = [4, 5, 6]
        b = None

        # Act
        result = sum_list_optional(a, b)

        # Assert
        assert result == [4, 5, 6]

    @pytest.mark.unit
    def test_sum_list_optional_both_values_no_duplicates(self) -> None:
        """Test combination when both lists have unique values."""
        # Arrange
        a = [1, 2, 3]
        b = [4, 5, 6]

        # Act
        result = sum_list_optional(a, b)

        # Assert
        # Result should contain all unique elements
        assert result is not None
        result_set = set(result)
        assert result_set == {1, 2, 3, 4, 5, 6}
        assert len(result) == 6

    @pytest.mark.unit
    def test_sum_list_optional_with_duplicates(self) -> None:
        """Test combination when lists have duplicate values."""
        # Arrange
        a = [1, 2, 3, 4]
        b = [3, 4, 5, 6]

        # Act
        result = sum_list_optional(a, b)

        # Assert
        # Duplicates should be removed
        assert result is not None
        result_set = set(result)
        assert result_set == {1, 2, 3, 4, 5, 6}
        assert len(result) == 6

    @pytest.mark.unit
    def test_sum_list_optional_empty_lists(self) -> None:
        """Test combination with empty lists."""
        # Arrange
        a: list[int] = []
        b: list[int] = []

        # Act
        result = sum_list_optional(a, b)

        # Assert
        # Empty lists are falsy, so function returns None
        assert result is None

    @pytest.mark.unit
    def test_sum_list_optional_one_empty_list(self) -> None:
        """Test combination when one list is empty."""
        # Arrange
        a = [1, 2, 3]
        b: list[int] = []

        # Act
        result = sum_list_optional(a, b)

        # Assert
        assert result == [1, 2, 3]

    @pytest.mark.unit
    def test_sum_list_optional_string_elements(self) -> None:
        """Test combination with string elements."""
        # Arrange
        a = ["apple", "banana"]
        b = ["cherry", "banana", "date"]

        # Act
        result = sum_list_optional(a, b)

        # Assert
        # Should remove duplicate "banana"
        assert result is not None
        result_set = set(result)
        assert result_set == {"apple", "banana", "cherry", "date"}
        assert len(result) == 4

    @pytest.mark.unit
    def test_sum_list_optional_mixed_types(self) -> None:
        """Test combination with mixed data types."""
        # Arrange
        a = [1, "hello", 3.14]
        b = [2, "hello", False]  # Use False instead of True to avoid 1/True collision

        # Act
        result = sum_list_optional(a, b)

        # Assert
        # Should remove duplicate "hello"
        expected_elements = {1, "hello", 3.14, 2, False}
        assert result is not None
        result_set = set(result)
        assert result_set == expected_elements
        assert len(result) == 5

    @pytest.mark.unit
    def test_sum_list_optional_identical_lists(self) -> None:
        """Test combination when both lists are identical."""
        # Arrange
        a = [1, 2, 3]
        b = [1, 2, 3]

        # Act
        result = sum_list_optional(a, b)

        # Assert
        # Should return unique elements only
        assert result is not None
        result_set = set(result)
        assert result_set == {1, 2, 3}
        assert len(result) == 3
