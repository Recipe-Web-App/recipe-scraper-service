"""Authentication and authorization module.

This module provides:
- JWT token creation and validation
- OAuth2 password flow
- Role-based access control (RBAC)
- FastAPI security dependencies
"""

from app.auth.dependencies import get_current_user, require_permissions, require_roles
from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.auth.permissions import Permission, Role


__all__ = [
    # RBAC
    "Permission",
    "Role",
    # JWT functions
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    # Dependencies
    "get_current_user",
    "require_permissions",
    "require_roles",
]
