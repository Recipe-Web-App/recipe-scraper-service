"""Example background tasks.

This module provides example task functions that demonstrate
how to write ARQ-compatible async tasks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.observability.logging import get_logger


if TYPE_CHECKING:
    from arq.jobs import Job

logger = get_logger(__name__)


async def send_notification(
    _ctx: dict[str, Any],
    user_id: str,
    message: str,
    *,
    channel: str = "email",
) -> dict[str, Any]:
    """Send a notification to a user.

    Args:
        _ctx: ARQ worker context containing shared state (unused).
        user_id: The user to notify.
        message: The notification message.
        channel: Notification channel (email, push, sms).

    Returns:
        Result dict with notification status.
    """
    logger.info(
        "Sending notification",
        user_id=user_id,
        channel=channel,
        message_length=len(message),
    )

    # TODO: Implement actual notification sending
    # This would integrate with email service, push notification service, etc.

    # Simulate notification sending
    return {
        "status": "sent",
        "user_id": user_id,
        "channel": channel,
    }


async def cleanup_expired_cache(_ctx: dict[str, Any]) -> dict[str, Any]:
    """Clean up expired cache entries.

    This is typically run as a cron job to maintain cache hygiene.

    Args:
        _ctx: ARQ worker context containing shared state (unused).

    Returns:
        Result dict with cleanup statistics.
    """
    logger.info("Starting cache cleanup")

    # TODO: Implement actual cache cleanup logic
    # This would scan and remove expired entries, orphaned keys, etc.

    cleaned_count = 0

    logger.info("Cache cleanup complete", cleaned_count=cleaned_count)

    return {
        "status": "completed",
        "cleaned_count": cleaned_count,
    }


async def process_recipe_scrape(
    _ctx: dict[str, Any],
    url: str,
    user_id: str,
) -> dict[str, Any]:
    """Process a recipe scraping request.

    Args:
        _ctx: ARQ worker context containing shared state (unused).
        url: The URL to scrape.
        user_id: The user who requested the scrape.

    Returns:
        Result dict with scraped recipe data or error.
    """
    logger.info(
        "Processing recipe scrape",
        url=url,
        user_id=user_id,
    )

    # TODO: Implement actual recipe scraping logic
    # This would:
    # 1. Fetch the URL
    # 2. Parse the HTML for recipe data
    # 3. Extract structured recipe information
    # 4. Store in database/cache
    # 5. Notify user of completion

    return {
        "status": "completed",
        "url": url,
        "user_id": user_id,
        "recipe": None,  # Would contain scraped recipe data
    }


def get_job_result(job: Job) -> dict[str, Any] | None:
    """Helper to safely get job result.

    Args:
        job: The ARQ job instance.

    Returns:
        Job result if available, None otherwise.
    """
    if job.result is None:
        return None
    return dict(job.result) if isinstance(job.result, dict) else {"result": job.result}
