"""Integration tests for ARQ workers and background jobs.

Tests cover:
- Job enqueueing with real Redis
- Task execution
- Job status retrieval
- ARQ pool lifecycle
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from arq.connections import ArqRedis, RedisSettings, create_pool

import app.workers.jobs as jobs_module
from app.workers.arq import (
    ARQ_QUEUE_NAME,
    WorkerSettings,
    get_redis_settings,
    shutdown,
    startup,
)
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
    from collections.abc import AsyncGenerator

    from app.core.config import Settings


pytestmark = pytest.mark.integration


class TestARQPoolManagement:
    """Tests for ARQ connection pool management."""

    @pytest.fixture
    async def arq_pool(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> AsyncGenerator[ArqRedis]:
        """Create ARQ pool connected to test Redis."""
        # Reset global pool state
        jobs_module._arq_pool = None

        with patch("app.workers.arq.get_settings", return_value=test_settings):
            pool = await create_pool(get_redis_settings())

        yield pool

        await pool.close()

    @pytest.mark.asyncio
    async def test_get_arq_pool_creates_pool(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> None:
        """Should create ARQ pool on first call."""
        # Reset global state
        jobs_module._arq_pool = None

        with (
            patch("app.workers.arq.get_settings", return_value=test_settings),
            patch(
                "app.workers.jobs.get_redis_settings", return_value=get_redis_settings()
            ),
            patch("app.workers.arq.get_settings", return_value=test_settings),
        ):
            pool = await get_arq_pool()

            assert pool is not None
            assert isinstance(pool, ArqRedis)

            # Cleanup
            await close_arq_pool()

    @pytest.mark.asyncio
    async def test_get_arq_pool_returns_same_instance(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> None:
        """Should return same pool instance on subsequent calls."""
        # Reset global state
        jobs_module._arq_pool = None

        with (
            patch("app.workers.arq.get_settings", return_value=test_settings),
            patch(
                "app.workers.jobs.get_redis_settings", return_value=get_redis_settings()
            ),
            patch("app.workers.arq.get_settings", return_value=test_settings),
        ):
            pool1 = await get_arq_pool()
            pool2 = await get_arq_pool()

            assert pool1 is pool2

            await close_arq_pool()

    @pytest.mark.asyncio
    async def test_close_arq_pool(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> None:
        """Should close pool and reset global state."""
        # Reset global state
        jobs_module._arq_pool = None

        with (
            patch("app.workers.arq.get_settings", return_value=test_settings),
            patch(
                "app.workers.jobs.get_redis_settings", return_value=get_redis_settings()
            ),
            patch("app.workers.arq.get_settings", return_value=test_settings),
        ):
            await get_arq_pool()
            assert jobs_module._arq_pool is not None

            await close_arq_pool()
            assert jobs_module._arq_pool is None


class TestJobEnqueuing:
    """Tests for job enqueueing with real Redis."""

    @pytest.fixture
    async def setup_arq(
        self,
        test_settings: Settings,
        redis_url: str,
    ) -> AsyncGenerator[None]:
        """Setup ARQ with test Redis."""
        # Reset global state
        jobs_module._arq_pool = None

        with (
            patch("app.workers.arq.get_settings", return_value=test_settings),
            patch(
                "app.workers.jobs.get_redis_settings", return_value=get_redis_settings()
            ),
        ):
            yield

        await close_arq_pool()

    @pytest.mark.asyncio
    async def test_enqueue_job(self, setup_arq: None) -> None:
        """Should enqueue a job successfully."""
        job = await enqueue_job("send_notification", "user-123", "Hello!")

        assert job is not None
        assert job.job_id is not None

    @pytest.mark.asyncio
    async def test_enqueue_job_with_custom_id(self, setup_arq: None) -> None:
        """Should enqueue job with custom ID."""
        custom_id = "my-custom-job-id"
        job = await enqueue_job(
            "send_notification",
            "user-123",
            "Hello!",
            _job_id=custom_id,
        )

        assert job is not None
        assert job.job_id == custom_id

    @pytest.mark.asyncio
    async def test_enqueue_notification(self, setup_arq: None) -> None:
        """Should enqueue notification job."""
        job = await enqueue_notification(
            user_id="user-456",
            message="Test notification",
            channel="push",
        )

        assert job is not None
        assert job.job_id is not None

    @pytest.mark.asyncio
    async def test_enqueue_recipe_scrape(self, setup_arq: None) -> None:
        """Should enqueue recipe scrape job."""
        job = await enqueue_recipe_scrape(
            url="https://example.com/recipe",
            user_id="user-789",
        )

        assert job is not None
        assert job.job_id is not None

    @pytest.mark.asyncio
    async def test_enqueued_job_has_valid_id(self, setup_arq: None) -> None:
        """Should create job with valid UUID-like ID."""
        job = await enqueue_job("send_notification", "user-123", "Test")

        assert job is not None
        # ARQ generates UUIDs for job IDs
        assert len(job.job_id) > 0


class TestJobStatus:
    """Tests for job status retrieval."""

    @pytest.fixture
    async def arq_pool_direct(
        self,
        test_settings: Settings,
    ) -> AsyncGenerator[ArqRedis]:
        """Create ARQ pool directly with test Redis settings."""
        # Create pool directly with test Redis settings
        redis_settings = RedisSettings(
            host=test_settings.redis.host,
            port=test_settings.redis.port,
            database=test_settings.redis.queue_db,
        )

        pool = await create_pool(redis_settings)

        # Inject into global state so get_job_status uses it
        jobs_module._arq_pool = pool

        yield pool

        # Cleanup
        await pool.close()
        jobs_module._arq_pool = None

    @pytest.mark.asyncio
    async def test_get_job_status_after_enqueue(
        self,
        arq_pool_direct: ArqRedis,
    ) -> None:
        """Should retrieve status for an enqueued job."""
        # Enqueue directly using the pool
        job = await arq_pool_direct.enqueue_job(
            "send_notification",
            "user-123",
            "Hello!",
        )
        assert job is not None

        # Get status - uses the same pool from global state
        status = await get_job_status(job.job_id)

        assert status is not None
        assert status["job_id"] == job.job_id
        assert status["function"] == "send_notification"
        assert "enqueue_time" in status
        assert status["enqueue_time"] is not None

    @pytest.mark.asyncio
    async def test_get_job_status_nonexistent(
        self,
        arq_pool_direct: ArqRedis,
    ) -> None:
        """Should return None or unknown for nonexistent job."""
        status = await get_job_status("nonexistent-job-id-12345")

        # ARQ returns None for jobs that don't exist
        assert status is None or status.get("status") == "unknown"

    @pytest.mark.asyncio
    async def test_get_job_status_with_custom_id(
        self,
        arq_pool_direct: ArqRedis,
    ) -> None:
        """Should retrieve status for job with custom ID."""
        custom_id = "my-test-job-status-check"

        job = await arq_pool_direct.enqueue_job(
            "send_notification",
            "user-456",
            "Test message",
            _job_id=custom_id,
        )
        assert job is not None
        assert job.job_id == custom_id

        status = await get_job_status(custom_id)

        assert status is not None
        assert status["job_id"] == custom_id


class TestTaskExecution:
    """Tests for direct task execution."""

    @pytest.mark.asyncio
    async def test_send_notification_task(self) -> None:
        """Should execute send_notification task."""
        ctx: dict = {}

        result = await send_notification(
            ctx,
            user_id="user-123",
            message="Test message",
            channel="email",
        )

        assert result["status"] == "sent"
        assert result["user_id"] == "user-123"
        assert result["channel"] == "email"

    @pytest.mark.asyncio
    async def test_cleanup_expired_cache_task(self) -> None:
        """Should execute cleanup_expired_cache task."""
        ctx: dict = {}

        result = await cleanup_expired_cache(ctx)

        assert result["status"] == "completed"
        assert "cleaned_count" in result

    @pytest.mark.asyncio
    async def test_process_recipe_scrape_task(self) -> None:
        """Should execute process_recipe_scrape task."""
        ctx: dict = {}

        result = await process_recipe_scrape(
            ctx,
            url="https://example.com/recipe",
            user_id="user-456",
        )

        assert result["status"] == "completed"
        assert result["url"] == "https://example.com/recipe"
        assert result["user_id"] == "user-456"


class TestWorkerLifecycle:
    """Tests for worker startup/shutdown handlers."""

    @pytest.mark.asyncio
    async def test_startup_handler(
        self,
        test_settings: Settings,
    ) -> None:
        """Should execute startup handler without error."""
        ctx: dict = {}

        with patch("app.workers.arq.get_settings", return_value=test_settings):
            await startup(ctx)

        assert "settings" in ctx

    @pytest.mark.asyncio
    async def test_shutdown_handler(self) -> None:
        """Should execute shutdown handler without error."""
        ctx: dict = {}

        # Should not raise
        await shutdown(ctx)

    def test_worker_settings_has_functions(self) -> None:
        """Should have registered task functions."""
        assert len(WorkerSettings.functions) > 0
        assert send_notification in WorkerSettings.functions
        assert cleanup_expired_cache in WorkerSettings.functions
        assert process_recipe_scrape in WorkerSettings.functions

    def test_worker_settings_has_cron_jobs(self) -> None:
        """Should have configured cron jobs."""
        assert len(WorkerSettings.cron_jobs) > 0


class TestARQEdgeCases:
    """Edge case tests for ARQ workers."""

    @pytest.fixture
    async def arq_pool_direct(
        self,
        test_settings: Settings,
    ) -> AsyncGenerator[ArqRedis]:
        """Create ARQ pool directly with test Redis settings."""
        redis_settings = RedisSettings(
            host=test_settings.redis.host,
            port=test_settings.redis.port,
            database=test_settings.redis.queue_db,
        )

        pool = await create_pool(redis_settings)
        jobs_module._arq_pool = pool

        yield pool

        await pool.close()
        jobs_module._arq_pool = None

    @pytest.mark.asyncio
    async def test_duplicate_job_id_handling(
        self,
        arq_pool_direct: ArqRedis,
    ) -> None:
        """Should handle duplicate job IDs appropriately."""
        custom_id = "duplicate-job-test-id"

        # Enqueue first job
        job1 = await arq_pool_direct.enqueue_job(
            "send_notification",
            "user-1",
            "First message",
            _job_id=custom_id,
        )
        assert job1 is not None

        # Try to enqueue with same ID - ARQ should return None or handle gracefully
        job2 = await arq_pool_direct.enqueue_job(
            "send_notification",
            "user-2",
            "Second message",
            _job_id=custom_id,
        )

        # ARQ returns None for duplicate job IDs
        assert job2 is None

    @pytest.mark.asyncio
    async def test_job_with_deferred_execution(
        self,
        arq_pool_direct: ArqRedis,
    ) -> None:
        """Should enqueue job with deferred execution."""
        # Defer by 5 seconds
        defer_until = datetime.now(UTC) + timedelta(seconds=5)

        job = await arq_pool_direct.enqueue_job(
            "send_notification",
            "user-123",
            "Deferred message",
            _defer_until=defer_until,
            _queue_name=ARQ_QUEUE_NAME,
        )

        assert job is not None
        assert job.job_id is not None

        # Check job info
        status = await get_job_status(job.job_id)
        assert status is not None
        # Job should be in deferred state
        assert status["status"] in ("deferred", "queued")

    @pytest.mark.asyncio
    async def test_concurrent_job_enqueueing(
        self,
        arq_pool_direct: ArqRedis,
    ) -> None:
        """Should handle many concurrent job enqueues."""

        async def enqueue_one(i: int) -> str | None:
            job = await arq_pool_direct.enqueue_job(
                "send_notification",
                f"user-{i}",
                f"Message {i}",
            )
            return job.job_id if job else None

        # Enqueue 50 jobs concurrently
        tasks = [enqueue_one(i) for i in range(50)]
        job_ids = await asyncio.gather(*tasks)

        # All should succeed
        successful = [jid for jid in job_ids if jid is not None]
        assert len(successful) == 50

        # All job IDs should be unique
        assert len(set(successful)) == 50

    @pytest.mark.asyncio
    async def test_job_with_complex_arguments(
        self,
        arq_pool_direct: ArqRedis,
    ) -> None:
        """Should handle complex argument types."""
        complex_args = {
            "nested": {"deep": {"value": [1, 2, 3]}},
            "list": ["a", "b", "c"],
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
        }

        job = await arq_pool_direct.enqueue_job(
            "process_recipe_scrape",
            "https://example.com",
            "user-123",
            metadata=complex_args,
        )

        assert job is not None
        assert job.job_id is not None

    @pytest.mark.asyncio
    async def test_enqueue_to_specific_queue(
        self,
        arq_pool_direct: ArqRedis,
    ) -> None:
        """Should enqueue to a specific queue name."""
        job = await arq_pool_direct.enqueue_job(
            "send_notification",
            "user-123",
            "Priority message",
            _queue_name="arq:priority",
        )

        assert job is not None
        assert job.job_id is not None

    @pytest.mark.asyncio
    async def test_job_expiration(
        self,
        arq_pool_direct: ArqRedis,
    ) -> None:
        """Should respect job expiration time."""
        # Job expires in 60 seconds if not picked up
        job = await arq_pool_direct.enqueue_job(
            "send_notification",
            "user-123",
            "Expiring message",
            _expires=60,
        )

        assert job is not None
        status = await get_job_status(job.job_id)
        assert status is not None

    @pytest.mark.asyncio
    async def test_multiple_jobs_same_function(
        self,
        arq_pool_direct: ArqRedis,
    ) -> None:
        """Should handle multiple jobs for the same function."""
        jobs = []
        for i in range(10):
            job = await arq_pool_direct.enqueue_job(
                "send_notification",
                f"user-{i}",
                f"Message {i}",
            )
            jobs.append(job)

        # All jobs should be created
        assert all(job is not None for job in jobs)

        # All job IDs should be unique
        job_ids = [job.job_id for job in jobs]
        assert len(set(job_ids)) == 10

        # Each job should be retrievable
        for job in jobs:
            status = await get_job_status(job.job_id)
            assert status is not None

    @pytest.mark.asyncio
    async def test_close_pool_multiple_times(
        self,
        test_settings: Settings,
    ) -> None:
        """Should handle closing pool multiple times safely."""
        jobs_module._arq_pool = None

        with (
            patch("app.workers.arq.get_settings", return_value=test_settings),
            patch(
                "app.workers.jobs.get_redis_settings",
                return_value=get_redis_settings(),
            ),
        ):
            await get_arq_pool()

            # Close multiple times - should not raise
            await close_arq_pool()
            await close_arq_pool()
            await close_arq_pool()

            assert jobs_module._arq_pool is None
