"""Helper functions for aggregation operations."""

from decimal import Decimal
from typing import Any


def combine_string_optional(a: str | None, b: str | None) -> str | None:
    """Combine two optional strings, preferring the first non-None value.

    Args:     a (str | None): First string value.     b (str | None): Second string
    value.

    Returns:     str | None: The first non-None value, or None if both are None.
    """
    return a or b


def combine_nutriscore_grades_optional(
    grade_a: str | None,
    grade_b: str | None,
) -> str | None:
    """Combine two nutriscore grades by taking the worst (highest) grade.

    Args:     grade_a (str | None): First nutriscore grade.     grade_b (str | None):
    Second nutriscore grade.

    Returns:     str | None: The worst grade, or None if both are None.
    """
    if not grade_a and not grade_b:
        return None
    if not grade_a:
        return grade_b
    if not grade_b:
        return grade_a

    # Return the worst grade (A is best, E is worst)
    grade_order = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}

    # Default to E if grade not recognized
    grade_a_val = grade_order.get(grade_a.upper(), 5)
    grade_b_val = grade_order.get(grade_b.upper(), 5)

    # Return the worse grade
    if grade_a_val >= grade_b_val:
        return grade_a.upper()
    return grade_b.upper()


def sum_decimal_optional(
    a: Decimal | None,
    b: Decimal | None,
    precision: str = "0.001",
) -> Decimal | None:
    """Add two optional decimals with specified precision.

    Args:     a (Decimal | None): First decimal to add.     b (Decimal | None): Second
    decimal to add.     precision (str): Quantization precision (default: "0.001" for 3
    decimal places).

    Returns:     Decimal | None: The sum of both decimals, or None if both were None.
    """
    if a is None and b is None:
        return None
    total = (a or Decimal(0)) + (b or Decimal(0))
    return total.quantize(Decimal(precision))


def sum_int_optional(a: int | None, b: int | None) -> int | None:
    """Add two optional integers.

    Args:     a (int | None): First integer to add.     b (int | None): Second integer
    to add.

    Returns:     int | None: The sum of both integers, or None if both were None.
    """
    if a is None and b is None:
        return None
    return (a or 0) + (b or 0)


def sum_list_optional(a: list[Any] | None, b: list[Any] | None) -> list[Any] | None:
    """Combine two lists, removing duplicates.

    Args:     a (list[Any] | None): First list to combine.     b (list[Any] | None):
    Second list to combine.

    Returns:     list[Any] | None: Combined list with unique elements.
    """
    return list(set((a or []) + (b or []))) if (a or b) else None
