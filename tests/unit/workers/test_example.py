"""Unit tests for example worker tasks.

Tests cover:
- send_notification task
- cleanup_expired_cache task
- process_recipe_scrape task
- get_job_result helper
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.workers.tasks.example import (
    cleanup_expired_cache,
    get_job_result,
    process_recipe_scrape,
    send_notification,
)


pytestmark = pytest.mark.unit


# =============================================================================
# Task Tests
# =============================================================================


class TestSendNotification:
    """Tests for send_notification task."""

    @pytest.mark.asyncio
    async def test_returns_sent_status(self) -> None:
        """Should return sent status."""
        ctx: dict[str, MagicMock] = {}

        result = await send_notification(
            ctx,
            user_id="user-123",
            message="Test notification",
        )

        assert result["status"] == "sent"
        assert result["user_id"] == "user-123"
        assert result["channel"] == "email"

    @pytest.mark.asyncio
    async def test_respects_channel_parameter(self) -> None:
        """Should use provided channel."""
        ctx: dict[str, MagicMock] = {}

        result = await send_notification(
            ctx,
            user_id="user-123",
            message="Test notification",
            channel="push",
        )

        assert result["channel"] == "push"


class TestCleanupExpiredCache:
    """Tests for cleanup_expired_cache task."""

    @pytest.mark.asyncio
    async def test_returns_completed_status(self) -> None:
        """Should return completed status."""
        ctx: dict[str, MagicMock] = {}

        result = await cleanup_expired_cache(ctx)

        assert result["status"] == "completed"
        assert "cleaned_count" in result


class TestProcessRecipeScrape:
    """Tests for process_recipe_scrape task."""

    @pytest.mark.asyncio
    async def test_returns_completed_status(self) -> None:
        """Should return completed status."""
        ctx: dict[str, MagicMock] = {}

        result = await process_recipe_scrape(
            ctx,
            url="https://example.com/recipe",
            user_id="user-123",
        )

        assert result["status"] == "completed"
        assert result["url"] == "https://example.com/recipe"
        assert result["user_id"] == "user-123"


# =============================================================================
# get_job_result Tests
# =============================================================================


class TestGetJobResult:
    """Tests for get_job_result helper function."""

    def test_returns_none_when_result_is_none(self) -> None:
        """Should return None when job.result is None."""
        mock_job = MagicMock()
        mock_job.result = None

        result = get_job_result(mock_job)

        assert result is None

    def test_returns_dict_when_result_is_dict(self) -> None:
        """Should return dict when job.result is a dict."""
        mock_job = MagicMock()
        mock_job.result = {"status": "completed", "value": 42}

        result = get_job_result(mock_job)

        assert result == {"status": "completed", "value": 42}

    def test_wraps_non_dict_result(self) -> None:
        """Should wrap non-dict result in a dict."""
        mock_job = MagicMock()
        mock_job.result = "simple string result"

        result = get_job_result(mock_job)

        assert result == {"result": "simple string result"}

    def test_wraps_numeric_result(self) -> None:
        """Should wrap numeric result in a dict."""
        mock_job = MagicMock()
        mock_job.result = 12345

        result = get_job_result(mock_job)

        assert result == {"result": 12345}

    def test_wraps_list_result(self) -> None:
        """Should wrap list result in a dict."""
        mock_job = MagicMock()
        mock_job.result = [1, 2, 3]

        result = get_job_result(mock_job)

        assert result == {"result": [1, 2, 3]}

    def test_converts_dict_to_new_dict(self) -> None:
        """Should create new dict from result dict."""
        original = {"key": "value"}
        mock_job = MagicMock()
        mock_job.result = original

        result = get_job_result(mock_job)

        # Should be a copy, not the same object
        assert result == original
        assert result is not original
