"""Job enqueue utilities.

This module provides functions for enqueuing background jobs
from the main application.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from arq.connections import ArqRedis, create_pool

from app.observability.logging import get_logger
from app.workers.arq import get_redis_settings


if TYPE_CHECKING:
    from arq.jobs import Job

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
    _queue_name: str | None = None,
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
        _queue_name: Optional queue name (default: arq:queue).
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
        job = await pool.job(job_id)

        if job is None:
            return None

        info = await job.info()
        if info is None:
            return {"job_id": job_id, "status": "unknown"}

        return {
            "job_id": job_id,
            "status": info.status,
            "function": info.function,
            "enqueue_time": info.enqueue_time.isoformat()
            if info.enqueue_time
            else None,
            "start_time": info.start_time.isoformat() if info.start_time else None,
            "finish_time": info.finish_time.isoformat() if info.finish_time else None,
            "success": info.success,
            "result": info.result,
        }
    except Exception:
        logger.exception("Failed to get job status", job_id=job_id)
        return None
