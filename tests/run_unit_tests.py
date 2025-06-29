"""Entrypoint for running all unit tests via Poetry script."""

import sys

import pytest


def main() -> None:
    """Run all tests in tests/unit/ (no marker filtering)."""
    sys.exit(pytest.main(["tests/unit/"]))


if __name__ == "__main__":
    main()
