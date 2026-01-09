"""E2E tests for background job processing.

Tests cover:
- Job enqueuing and execution flow
- Job status tracking
- Complete job lifecycle
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from arq import create_pool
from arq.connections import RedisSettings
from arq.jobs import Job, JobStatus

import app.workers.jobs as jobs_module
from app.workers.jobs import (
    close_arq_pool,
    enqueue_job,
    enqueue_notification,
    enqueue_recipe_scrape,
    get_arq_pool,
    get_job_status,
)
from app.workers.tasks.example import (
    cleanup_expired_cache,
    process_recipe_scrape,
    send_notification,
)


if TYPE_CHECKING:
    from arq import ArqRedis

    from app.core.config import Settings


pytestmark = pytest.mark.e2e


class TestJobEnqueuing:
    """Tests for job enqueue operations."""

    @pytest.fixture
    async def arq_pool(
        self,
        test_settings: Settings,
    ) -> ArqRedis:
        """Create ARQ pool with test settings."""
        pool = await create_pool(
            RedisSettings(
                host=test_settings.REDIS_HOST,
                port=test_settings.REDIS_PORT,
                database=test_settings.REDIS_QUEUE_DB,
            ),
        )
        yield pool
        await pool.aclose()

    @pytest.fixture(autouse=True)
    async def reset_arq_pool(self) -> None:
        """Reset ARQ pool state between tests."""
        jobs_module._arq_pool = None

        yield

        await close_arq_pool()

    @pytest.mark.asyncio
    async def test_enqueue_notification_job(
        self,
        test_settings: Settings,
    ) -> None:
        """Should enqueue notification job successfully."""
        with patch("app.workers.arq.get_settings", return_value=test_settings):
            job = await enqueue_notification(
                user_id="test-user-123",
                message="Test notification message",
                channel="email",
            )

        assert job is not None
        assert job.job_id is not None

    @pytest.mark.asyncio
    async def test_enqueue_recipe_scrape_job(
        self,
        test_settings: Settings,
    ) -> None:
        """Should enqueue recipe scrape job successfully."""
        with patch("app.workers.arq.get_settings", return_value=test_settings):
            job = await enqueue_recipe_scrape(
                url="https://example.com/recipe",
                user_id="test-user-456",
            )

        assert job is not None
        assert job.job_id is not None

    @pytest.mark.asyncio
    async def test_enqueue_job_with_custom_id(
        self,
        test_settings: Settings,
    ) -> None:
        """Should enqueue job with custom ID."""
        custom_id = "custom-job-id-789"

        with patch("app.workers.arq.get_settings", return_value=test_settings):
            job = await enqueue_job(
                "send_notification",
                "user-id",
                "message",
                _job_id=custom_id,
            )

        assert job is not None
        assert job.job_id == custom_id

    @pytest.mark.asyncio
    async def test_enqueue_deferred_job(
        self,
        test_settings: Settings,
    ) -> None:
        """Should enqueue job with deferred execution."""
        defer_time = datetime.now(UTC) + timedelta(minutes=5)

        with patch("app.workers.arq.get_settings", return_value=test_settings):
            job = await enqueue_job(
                "send_notification",
                "user-id",
                "deferred message",
                _defer_until=defer_time,
            )

        assert job is not None
        assert job.job_id is not None


class TestJobStatus:
    """Tests for job status tracking."""

    @pytest.fixture(autouse=True)
    async def reset_arq_pool(self) -> None:
        """Reset ARQ pool state between tests."""
        jobs_module._arq_pool = None

        yield

        await close_arq_pool()

    @pytest.mark.asyncio
    async def test_get_job_status_for_enqueued_job(
        self,
        test_settings: Settings,
    ) -> None:
        """Should return status for enqueued job."""
        with patch("app.workers.arq.get_settings", return_value=test_settings):
            job = await enqueue_notification(
                user_id="status-test-user",
                message="Status test message",
            )

            assert job is not None

            status = await get_job_status(job.job_id)

        assert status is not None
        assert status["job_id"] == job.job_id
        assert status["function"] == "send_notification"
        assert status["status"] in ("queued", "deferred", "in_progress")

    @pytest.mark.asyncio
    async def test_get_job_status_for_unknown_job(
        self,
        test_settings: Settings,
    ) -> None:
        """Should return unknown status for non-existent job."""
        with patch("app.workers.arq.get_settings", return_value=test_settings):
            status = await get_job_status("non-existent-job-id")

        assert status is not None
        assert status["status"] == "unknown"


class TestJobExecution:
    """Tests for job execution with mocked worker."""

    @pytest.fixture
    async def arq_pool(
        self,
        test_settings: Settings,
    ) -> ArqRedis:
        """Create ARQ pool with test settings."""
        pool = await create_pool(
            RedisSettings(
                host=test_settings.REDIS_HOST,
                port=test_settings.REDIS_PORT,
                database=test_settings.REDIS_QUEUE_DB,
            ),
        )
        yield pool
        await pool.aclose()

    @pytest.mark.asyncio
    async def test_send_notification_task_execution(
        self,
        arq_pool: ArqRedis,
    ) -> None:
        """Should execute send_notification task directly."""
        ctx: dict = {}  # Empty context

        result = await send_notification(
            ctx,
            user_id="exec-test-user",
            message="Direct execution test",
            channel="push",
        )

        assert result["status"] == "sent"
        assert result["user_id"] == "exec-test-user"
        assert result["channel"] == "push"

    @pytest.mark.asyncio
    async def test_cleanup_expired_cache_task_execution(
        self,
        arq_pool: ArqRedis,
    ) -> None:
        """Should execute cleanup_expired_cache task directly."""
        ctx: dict = {}

        result = await cleanup_expired_cache(ctx)

        assert result["status"] == "completed"
        assert "cleaned_count" in result

    @pytest.mark.asyncio
    async def test_process_recipe_scrape_task_execution(
        self,
        arq_pool: ArqRedis,
    ) -> None:
        """Should execute process_recipe_scrape task directly."""
        ctx: dict = {}

        result = await process_recipe_scrape(
            ctx,
            url="https://example.com/my-recipe",
            user_id="scrape-user-123",
        )

        assert result["status"] == "completed"
        assert result["url"] == "https://example.com/my-recipe"
        assert result["user_id"] == "scrape-user-123"


class TestJobLifecycle:
    """Tests for complete job lifecycle."""

    @pytest.fixture
    async def arq_pool(
        self,
        test_settings: Settings,
    ) -> ArqRedis:
        """Create ARQ pool with test settings."""
        pool = await create_pool(
            RedisSettings(
                host=test_settings.REDIS_HOST,
                port=test_settings.REDIS_PORT,
                database=test_settings.REDIS_QUEUE_DB,
            ),
        )
        yield pool
        await pool.aclose()

    @pytest.fixture(autouse=True)
    async def reset_arq_pool(self) -> None:
        """Reset ARQ pool state between tests."""
        jobs_module._arq_pool = None

        yield

        await close_arq_pool()

    @pytest.mark.asyncio
    async def test_multiple_jobs_enqueue_sequence(
        self,
        test_settings: Settings,
    ) -> None:
        """Should enqueue multiple jobs in sequence."""
        jobs = []

        with patch("app.workers.arq.get_settings", return_value=test_settings):
            for i in range(5):
                job = await enqueue_notification(
                    user_id=f"user-{i}",
                    message=f"Message {i}",
                )
                jobs.append(job)

        # All jobs should be enqueued
        assert len(jobs) == 5
        assert all(job is not None for job in jobs)

        # All job IDs should be unique
        job_ids = [job.job_id for job in jobs]
        assert len(set(job_ids)) == 5

    @pytest.mark.asyncio
    async def test_concurrent_job_enqueuing(
        self,
        test_settings: Settings,
    ) -> None:
        """Should handle concurrent job enqueuing."""
        # Initialize pool once before concurrent operations to avoid race
        with patch("app.workers.arq.get_settings", return_value=test_settings):
            await get_arq_pool()

            async def enqueue_one(index: int) -> Job | None:
                return await enqueue_notification(
                    user_id=f"concurrent-user-{index}",
                    message=f"Concurrent message {index}",
                )

            tasks = [enqueue_one(i) for i in range(10)]
            jobs = await asyncio.gather(*tasks)

        # All jobs should be enqueued
        successful_jobs = [j for j in jobs if j is not None]
        assert len(successful_jobs) == 10

    @pytest.mark.asyncio
    async def test_job_with_expiration(
        self,
        test_settings: Settings,
        arq_pool: ArqRedis,
    ) -> None:
        """Should handle job with short expiration."""
        with patch("app.workers.arq.get_settings", return_value=test_settings):
            job = await enqueue_job(
                "send_notification",
                "user-id",
                "expiring message",
                _expires=1,  # 1 second expiration
            )

        assert job is not None

        # Job should be queued initially
        job_obj = Job(job.job_id, arq_pool)
        status = await job_obj.status()
        assert status in (JobStatus.queued, JobStatus.deferred)

        # Wait for expiration
        await asyncio.sleep(2)

        # Check status after expiration
        # Note: Job may still appear queued until worker processes it
        status_after = await job_obj.status()
        assert status_after in (JobStatus.queued, JobStatus.not_found)

    @pytest.mark.asyncio
    async def test_arq_pool_reuse(
        self,
        test_settings: Settings,
    ) -> None:
        """Should reuse ARQ pool across multiple enqueue calls."""
        with patch("app.workers.arq.get_settings", return_value=test_settings):
            # First call creates pool
            pool1 = await get_arq_pool()

            # Second call should reuse
            pool2 = await get_arq_pool()

            assert pool1 is pool2

            # Enqueue using shared pool
            job1 = await enqueue_notification("user1", "msg1")
            job2 = await enqueue_notification("user2", "msg2")

            assert job1 is not None
            assert job2 is not None


class TestJobEdgeCases:
    """Edge case tests for background jobs."""

    @pytest.fixture(autouse=True)
    async def reset_arq_pool(self) -> None:
        """Reset ARQ pool state between tests."""
        jobs_module._arq_pool = None

        yield

        await close_arq_pool()

    @pytest.mark.asyncio
    async def test_enqueue_with_complex_arguments(
        self,
        test_settings: Settings,
    ) -> None:
        """Should handle complex argument types."""
        with patch("app.workers.arq.get_settings", return_value=test_settings):
            job = await enqueue_job(
                "send_notification",
                "user-with-complex-args",
                "Message with unicode: 🎉",
                channel="email",
            )

        assert job is not None

    @pytest.mark.asyncio
    async def test_enqueue_with_very_long_message(
        self,
        test_settings: Settings,
    ) -> None:
        """Should handle very long message content."""
        long_message = "x" * 10000  # 10KB message

        with patch("app.workers.arq.get_settings", return_value=test_settings):
            job = await enqueue_notification(
                user_id="long-message-user",
                message=long_message,
            )

        assert job is not None

    @pytest.mark.asyncio
    async def test_duplicate_job_id_behavior(
        self,
        test_settings: Settings,
    ) -> None:
        """Should handle duplicate job IDs appropriately."""
        job_id = "duplicate-test-id"

        with patch("app.workers.arq.get_settings", return_value=test_settings):
            # First enqueue
            job1 = await enqueue_job(
                "send_notification",
                "user1",
                "msg1",
                _job_id=job_id,
            )

            # Second enqueue with same ID
            job2 = await enqueue_job(
                "send_notification",
                "user2",
                "msg2",
                _job_id=job_id,
            )

        # First job should succeed
        assert job1 is not None

        # Second may be None (duplicate) or same ID depending on ARQ behavior
        if job2 is not None:
            assert job2.job_id == job_id

    @pytest.mark.asyncio
    async def test_pool_close_and_recreate(
        self,
        test_settings: Settings,
    ) -> None:
        """Should handle pool close and recreation."""
        with patch("app.workers.arq.get_settings", return_value=test_settings):
            # Create and use pool
            pool1 = await get_arq_pool()
            await enqueue_notification("user1", "msg1")

            # Close pool
            await close_arq_pool()

            # Recreate and use again
            pool2 = await get_arq_pool()
            job = await enqueue_notification("user2", "msg2")

        # Should get new pool instance
        assert pool1 is not pool2
        assert job is not None

    @pytest.mark.asyncio
    async def test_enqueue_with_special_characters_in_user_id(
        self,
        test_settings: Settings,
    ) -> None:
        """Should handle special characters in arguments."""
        special_user_ids = [
            "user@example.com",
            "user+tag@domain.com",
            "user/with/slashes",
            "user:with:colons",
        ]

        with patch("app.workers.arq.get_settings", return_value=test_settings):
            for user_id in special_user_ids:
                job = await enqueue_notification(
                    user_id=user_id,
                    message="Test message",
                )
                assert job is not None, f"Failed for user_id: {user_id}"
