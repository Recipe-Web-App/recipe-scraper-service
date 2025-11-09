"""Dependency injection for NotificationService."""

from app.deps.service_token_manager import get_service_token_manager
from app.services.downstream.notification_service import NotificationService

# Singleton instance
_notification_service: NotificationService | None = None


def get_notification_service() -> NotificationService:
    """Get or create the singleton NotificationService instance.

    Returns:
        NotificationService instance
    """
    global _notification_service

    if _notification_service is None:
        token_manager = get_service_token_manager()
        _notification_service = NotificationService(token_manager=token_manager)

    return _notification_service
