"""Dependency injection for UserManagementService."""

from app.deps.service_token_manager import get_service_token_manager
from app.services.downstream.user_management_service import UserManagementService

# Singleton instance
_user_management_service: UserManagementService | None = None


def get_user_management_service() -> UserManagementService:
    """Get or create the singleton UserManagementService instance.

    Returns:
        UserManagementService instance
    """
    global _user_management_service

    if _user_management_service is None:
        token_manager = get_service_token_manager()
        _user_management_service = UserManagementService(token_manager=token_manager)

    return _user_management_service
