"""Authentication schemas for request/response validation."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class TokenRequest(BaseModel):
    """OAuth2 password grant token request."""

    username: str = Field(..., description="Username or email")
    password: str = Field(..., min_length=8, description="User password")


class TokenResponse(BaseModel):
    """Token response for successful authentication."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""

    refresh_token: str = Field(..., description="Valid refresh token")


class TokenInfo(BaseModel):
    """Information about a decoded token."""

    sub: str = Field(..., description="Token subject (user ID)")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    type: str = Field(..., description="Token type (access/refresh)")
    roles: list[str] = Field(default_factory=list, description="User roles")
    permissions: list[str] = Field(default_factory=list, description="Direct permissions")


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password (min 8 characters)",
    )
    full_name: str | None = Field(None, max_length=100, description="User's full name")


class UserResponse(BaseModel):
    """Schema for user response."""

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str | None = Field(None, description="User's full name")
    roles: list[str] = Field(default_factory=list, description="User roles")
    is_active: bool = Field(default=True, description="Whether user is active")


class PasswordChange(BaseModel):
    """Schema for password change request."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password (min 8 characters)",
    )


class PasswordReset(BaseModel):
    """Schema for password reset request."""

    email: EmailStr = Field(..., description="Email for password reset")


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str = Field(..., description="Password reset token")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password (min 8 characters)",
    )
