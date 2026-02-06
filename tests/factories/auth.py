"""Auth-related factories for generating test data.

Uses polyfactory for consistent test data generation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from polyfactory.factories.pydantic_factory import ModelFactory

from app.auth.jwt import TokenPayload
from app.auth.permissions import Permission, Role


class TokenPayloadFactory(ModelFactory[TokenPayload]):
    """Factory for generating TokenPayload instances."""

    __model__ = TokenPayload

    @classmethod
    def sub(cls) -> str:
        """Generate a unique subject (user ID)."""
        return f"user-{uuid4().hex[:12]}"

    @classmethod
    def exp(cls) -> datetime:
        """Generate expiration time (30 minutes from now)."""
        return datetime.now(UTC) + timedelta(minutes=30)

    @classmethod
    def iat(cls) -> datetime:
        """Generate issued-at time (now)."""
        return datetime.now(UTC)

    @classmethod
    def jti(cls) -> str | None:
        """Generate JWT ID."""
        return uuid4().hex

    @classmethod
    def type(cls) -> str:
        """Token type."""
        return "access"

    @classmethod
    def roles(cls) -> list[str]:
        """Default roles."""
        return [Role.USER]

    @classmethod
    def permissions(cls) -> list[str]:
        """Default permissions."""
        return []

    @classmethod
    def access_token(cls, user_id: str | None = None, **kwargs: Any) -> TokenPayload:
        """Create an access token payload."""
        return cls.build(
            sub=user_id or cls.sub(),
            type="access",
            **kwargs,
        )

    @classmethod
    def refresh_token(cls, user_id: str | None = None, **kwargs: Any) -> TokenPayload:
        """Create a refresh token payload."""
        return cls.build(
            sub=user_id or cls.sub(),
            type="refresh",
            exp=datetime.now(UTC) + timedelta(days=7),
            roles=[],
            permissions=[],
            **kwargs,
        )

    @classmethod
    def expired(cls, user_id: str | None = None, **kwargs: Any) -> TokenPayload:
        """Create an expired token payload."""
        return cls.build(
            sub=user_id or cls.sub(),
            exp=datetime.now(UTC) - timedelta(hours=1),
            iat=datetime.now(UTC) - timedelta(hours=2),
            **kwargs,
        )

    @classmethod
    def admin(cls, user_id: str | None = None, **kwargs: Any) -> TokenPayload:
        """Create an admin token payload."""
        return cls.build(
            sub=user_id or f"admin-{uuid4().hex[:8]}",
            roles=[Role.ADMIN],
            permissions=[str(p) for p in Permission],
            **kwargs,
        )

    @classmethod
    def premium(cls, user_id: str | None = None, **kwargs: Any) -> TokenPayload:
        """Create a premium user token payload."""
        return cls.build(
            sub=user_id or f"premium-{uuid4().hex[:8]}",
            roles=[Role.PREMIUM],
            **kwargs,
        )


class UserDataFactory:
    """Factory for generating user data dictionaries.

    Not a Pydantic model factory since User model isn't defined yet.
    """

    @classmethod
    def build(
        cls,
        user_id: str | None = None,
        email: str | None = None,
        name: str | None = None,
        roles: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Build a user data dictionary."""
        uid = user_id or f"user-{uuid4().hex[:12]}"
        return {
            "id": uid,
            "email": email or f"{uid}@example.com",
            "name": name or f"Test User {uid[:8]}",
            "roles": roles or [Role.USER],
            "is_active": True,
            "created_at": datetime.now(UTC).isoformat(),
            **kwargs,
        }

    @classmethod
    def admin(cls, **kwargs: Any) -> dict[str, Any]:
        """Build an admin user data dictionary."""
        return cls.build(
            user_id=f"admin-{uuid4().hex[:8]}",
            roles=[Role.ADMIN],
            **kwargs,
        )

    @classmethod
    def premium(cls, **kwargs: Any) -> dict[str, Any]:
        """Build a premium user data dictionary."""
        return cls.build(
            user_id=f"premium-{uuid4().hex[:8]}",
            roles=[Role.PREMIUM],
            **kwargs,
        )

    @classmethod
    def service(cls, **kwargs: Any) -> dict[str, Any]:
        """Build a service account data dictionary."""
        return cls.build(
            user_id=f"service-{uuid4().hex[:8]}",
            roles=[Role.SERVICE],
            email=None,
            name="Service Account",
            **kwargs,
        )
