#!/usr/bin/env python3
"""Test runner scripts for pytest.

Provides entry points for running different test suites.
"""

from __future__ import annotations

import os
import sys

import pytest


# Ensure APP_ENV is set to 'test' for all test runs
os.environ.setdefault("APP_ENV", "test")


def run_unit() -> int:
    """Run unit tests only."""
    return pytest.main(["-m", "unit", "-v", *sys.argv[1:]])


def run_integration() -> int:
    """Run integration tests only."""
    return pytest.main(["-m", "integration", "-v", *sys.argv[1:]])


def run_e2e() -> int:
    """Run end-to-end tests only."""
    return pytest.main(["-m", "e2e", "-v", *sys.argv[1:]])


def run_performance() -> int:
    """Run performance/benchmark tests only."""
    return pytest.main(["-m", "performance", "-v", *sys.argv[1:]])


def run_all() -> int:
    """Run all tests."""
    return pytest.main(["-v", *sys.argv[1:]])


def run_coverage() -> int:
    """Run tests with coverage report."""
    return pytest.main(
        [
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html",
            *sys.argv[1:],
        ]
    )


if __name__ == "__main__":
    sys.exit(run_unit())
