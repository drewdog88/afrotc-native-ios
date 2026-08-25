"""Profile + 2FA schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr

from app.schemas.common import Message, ORMModel  # noqa: F401


class ProfileUpdate(BaseModel):
    """Self-service profile update (any authenticated user)."""

    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None


class TwoFAStatus(ORMModel):
    """2FA enablement status for the current user."""

    enabled: bool
    method: str | None = None
    enrollment_prompted: bool = False


class TwoFAEnrollRequest(BaseModel):
    """Request to begin email 2FA enrollment."""

    method: str = "email"


class TwoFAVerifyRequest(BaseModel):
    """Verify a one-time code to complete 2FA enrollment."""

    code: str
