"""Job enqueue utilities.

This module provides functions for enqueuing background jobs
from the main application.
"""

from __future__ import annotations

import contextlib
from typing import Any

from arq.connections import ArqRedis, create_pool
from arq.jobs import Job

from app.core.config import get_settings
from app.observability.logging import get_logger
from app.workers.arq import ARQ_QUEUE_NAME, get_redis_settings


logger = get_logger(__name__)

# Global connection pool for enqueuing jobs
_arq_pool: ArqRedis | None = None


async def get_arq_pool() -> ArqRedis:
    """Get or create the ARQ connection pool.

    Returns:
        ARQ Redis connection pool for enqueuing jobs.
    """
    global _arq_pool  # noqa: PLW0603

    if _arq_pool is None:
        _arq_pool = await create_pool(get_redis_settings())
        logger.debug("Created ARQ connection pool")

    return _arq_pool


async def close_arq_pool() -> None:
    """Close the ARQ connection pool.

    Should be called during application shutdown.
    """
    global _arq_pool  # noqa: PLW0603

    if _arq_pool is not None:
        await _arq_pool.close()
        _arq_pool = None
        logger.debug("Closed ARQ connection pool")


async def enqueue_job(
    function_name: str,
    *args: Any,
    _job_id: str | None = None,
    _queue_name: str = ARQ_QUEUE_NAME,
    _defer_until: Any | None = None,
    _defer_by: float | None = None,
    _expires: float | None = None,
    _job_try: int | None = None,
    **kwargs: Any,
) -> Job | None:
    """Enqueue a background job.

    Args:
        function_name: Name of the task function to execute.
        *args: Positional arguments for the task.
        _job_id: Optional unique job ID.
        _queue_name: Queue name (default: scraper:queue:jobs).
        _defer_until: Optional datetime to defer job execution.
        _defer_by: Optional seconds to defer job execution.
        _expires: Optional job expiration time in seconds.
        _job_try: Optional retry attempt number.
        **kwargs: Keyword arguments for the task.

    Returns:
        Job instance if enqueued successfully, None otherwise.
    """
    try:
        pool = await get_arq_pool()
        job = await pool.enqueue_job(
            function_name,
            *args,
            _job_id=_job_id,
            _queue_name=_queue_name,
            _defer_until=_defer_until,
            _defer_by=_defer_by,
            _expires=_expires,
            _job_try=_job_try,
            **kwargs,
        )
        logger.info(
            "Enqueued job",
            function=function_name,
            job_id=job.job_id if job else None,
        )
    except Exception:
        logger.exception("Failed to enqueue job", function=function_name)
        return None
    else:
        return job


async def enqueue_notification(
    user_id: str,
    message: str,
    *,
    channel: str = "email",
) -> Job | None:
    """Enqueue a notification job.

    Convenience wrapper for the send_notification task.

    Args:
        user_id: The user to notify.
        message: The notification message.
        channel: Notification channel (email, push, sms).

    Returns:
        Job instance if enqueued successfully.
    """
    return await enqueue_job(
        "send_notification",
        user_id,
        message,
        channel=channel,
    )


async def enqueue_recipe_scrape(
    url: str,
    user_id: str,
) -> Job | None:
    """Enqueue a recipe scraping job.

    Convenience wrapper for the process_recipe_scrape task.

    Args:
        url: The URL to scrape.
        user_id: The user who requested the scrape.

    Returns:
        Job instance if enqueued successfully.
    """
    return await enqueue_job(
        "process_recipe_scrape",
        url,
        user_id,
    )


async def get_job_status(job_id: str) -> dict[str, Any] | None:
    """Get the status of a job.

    Args:
        job_id: The job ID to check.

    Returns:
        Job status dict or None if not found.
    """
    try:
        pool = await get_arq_pool()
        job = Job(job_id, pool, _queue_name=ARQ_QUEUE_NAME)

        # Get job definition (enqueue info)
        info = await job.info()
        if info is None:
            return {"job_id": job_id, "status": "unknown"}

        # Get job status separately
        status = await job.status()

        # Get result if job is complete
        result = None
        if status.name in ("complete", "not_found"):
            with contextlib.suppress(Exception):
                result = await job.result(timeout=0)

        return {
            "job_id": job_id,
            "status": status.name,
            "function": info.function,
            "enqueue_time": info.enqueue_time.isoformat()
            if info.enqueue_time
            else None,
            "job_try": info.job_try,
            "result": result,
        }
    except Exception:
        logger.exception("Failed to get job status", job_id=job_id)
        return None


async def enqueue_popular_recipes_refresh() -> Job | None:
    """Enqueue popular recipes refresh job.

    Uses a fixed job_id from config to prevent duplicate jobs.
    ARQ behavior with fixed job_id:
    - If job with this ID is already queued → returns existing job (no duplicate)
    - If job with this ID is in-progress → returns existing job (no duplicate)
    - If no job exists → creates new job

    Returns:
        Job instance if enqueued successfully.
    """
    settings = get_settings()
    job_id = settings.arq.job_ids.popular_recipes_refresh

    return await enqueue_job(
        "refresh_popular_recipes",
        _job_id=job_id,
    )
