"""Unit tests for job enqueue utilities.

Tests cover:
- ARQ pool management
- Job enqueueing
- Convenience wrappers
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.workers.jobs as jobs_module
from app.workers.jobs import (
    close_arq_pool,
    enqueue_job,
    enqueue_notification,
    enqueue_recipe_scrape,
    get_arq_pool,
    get_job_status,
)


if TYPE_CHECKING:
    from collections.abc import Generator


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def reset_arq_pool() -> Generator[None]:
    """Reset the global ARQ pool before and after each test."""
    jobs_module._arq_pool = None
    yield
    jobs_module._arq_pool = None


class TestGetArqPool:
    """Tests for get_arq_pool function."""

    @pytest.mark.asyncio
    async def test_creates_pool_on_first_call(self) -> None:
        """Should create pool on first call."""
        mock_pool = AsyncMock()

        with (
            patch(
                "app.workers.jobs.create_pool", return_value=mock_pool
            ) as mock_create,
            patch("app.workers.jobs.get_redis_settings") as mock_settings,
        ):
            result = await get_arq_pool()

            mock_create.assert_called_once()
            mock_settings.assert_called_once()
            assert result is mock_pool

    @pytest.mark.asyncio
    async def test_reuses_existing_pool(self) -> None:
        """Should reuse existing pool on subsequent calls."""
        mock_pool = AsyncMock()
        jobs_module._arq_pool = mock_pool

        with patch("app.workers.jobs.create_pool") as mock_create:
            result = await get_arq_pool()

            mock_create.assert_not_called()
            assert result is mock_pool


class TestCloseArqPool:
    """Tests for close_arq_pool function."""

    @pytest.mark.asyncio
    async def test_closes_pool_when_exists(self) -> None:
        """Should close pool when it exists."""
        mock_pool = AsyncMock()
        jobs_module._arq_pool = mock_pool

        await close_arq_pool()

        mock_pool.close.assert_called_once()
        assert jobs_module._arq_pool is None

    @pytest.mark.asyncio
    async def test_does_nothing_when_no_pool(self) -> None:
        """Should do nothing when no pool exists."""
        # Should not raise
        await close_arq_pool()

        assert jobs_module._arq_pool is None


class TestEnqueueJob:
    """Tests for enqueue_job function."""

    @pytest.mark.asyncio
    async def test_enqueues_job_successfully(self) -> None:
        """Should enqueue job and return Job instance."""
        mock_job = MagicMock()
        mock_job.job_id = "test-job-123"

        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=mock_job)
        jobs_module._arq_pool = mock_pool

        result = await enqueue_job("test_function", "arg1", kwarg1="value1")

        mock_pool.enqueue_job.assert_called_once()
        assert result is mock_job

    @pytest.mark.asyncio
    async def test_returns_none_on_error(self) -> None:
        """Should return None on error."""
        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(side_effect=Exception("Connection error"))
        jobs_module._arq_pool = mock_pool

        result = await enqueue_job("test_function")

        assert result is None

    @pytest.mark.asyncio
    async def test_passes_job_options(self) -> None:
        """Should pass job options to pool."""
        mock_job = MagicMock()
        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=mock_job)
        jobs_module._arq_pool = mock_pool

        await enqueue_job(
            "test_function",
            "arg1",
            _job_id="custom-id",
            _queue_name="custom-queue",
            _defer_by=60.0,
        )

        call_kwargs = mock_pool.enqueue_job.call_args.kwargs
        assert call_kwargs["_job_id"] == "custom-id"
        assert call_kwargs["_queue_name"] == "custom-queue"
        assert call_kwargs["_defer_by"] == 60.0


class TestEnqueueNotification:
    """Tests for enqueue_notification function."""

    @pytest.mark.asyncio
    async def test_enqueues_notification_job(self) -> None:
        """Should enqueue send_notification job."""
        with patch("app.workers.jobs.enqueue_job") as mock_enqueue:
            mock_enqueue.return_value = MagicMock()

            await enqueue_notification("user-123", "Hello!", channel="push")

            mock_enqueue.assert_called_once_with(
                "send_notification",
                "user-123",
                "Hello!",
                channel="push",
            )

    @pytest.mark.asyncio
    async def test_uses_email_as_default_channel(self) -> None:
        """Should use email as default notification channel."""
        with patch("app.workers.jobs.enqueue_job") as mock_enqueue:
            mock_enqueue.return_value = MagicMock()

            await enqueue_notification("user-123", "Hello!")

            call_kwargs = mock_enqueue.call_args.kwargs
            assert call_kwargs["channel"] == "email"


class TestEnqueueRecipeScrape:
    """Tests for enqueue_recipe_scrape function."""

    @pytest.mark.asyncio
    async def test_enqueues_scrape_job(self) -> None:
        """Should enqueue process_recipe_scrape job."""
        with patch("app.workers.jobs.enqueue_job") as mock_enqueue:
            mock_enqueue.return_value = MagicMock()

            await enqueue_recipe_scrape("https://example.com/recipe", "user-456")

            mock_enqueue.assert_called_once_with(
                "process_recipe_scrape",
                "https://example.com/recipe",
                "user-456",
            )


class TestGetJobStatus:
    """Tests for get_job_status function."""

    @pytest.mark.asyncio
    async def test_returns_status_for_existing_job(self) -> None:
        """Should return status dict for existing job."""
        mock_info = MagicMock()
        mock_info.status = "complete"
        mock_info.function = "test_function"
        mock_info.enqueue_time = MagicMock()
        mock_info.enqueue_time.isoformat.return_value = "2024-01-01T00:00:00"
        mock_info.start_time = None
        mock_info.finish_time = None
        mock_info.success = True
        mock_info.result = "done"

        mock_job = AsyncMock()
        mock_job.info = AsyncMock(return_value=mock_info)

        mock_pool = AsyncMock()
        mock_pool.job = AsyncMock(return_value=mock_job)
        jobs_module._arq_pool = mock_pool

        result = await get_job_status("job-123")

        assert result is not None
        assert result["job_id"] == "job-123"
        assert result["status"] == "complete"
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_job(self) -> None:
        """Should return None for non-existent job."""
        mock_pool = AsyncMock()
        mock_pool.job = AsyncMock(return_value=None)
        jobs_module._arq_pool = mock_pool

        result = await get_job_status("nonexistent-job")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_error(self) -> None:
        """Should return None on error."""
        mock_pool = AsyncMock()
        mock_pool.job = AsyncMock(side_effect=Exception("Redis error"))
        jobs_module._arq_pool = mock_pool

        result = await get_job_status("job-123")

        assert result is None
