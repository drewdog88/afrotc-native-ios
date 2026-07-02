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
    """2FA enablement status."""

    enabled: bool


class TwoFASetupResponse(BaseModel):
    """Response when initiating 2FA setup — secret + provisioning URI."""

    secret: str
    otpauth_uri: str


class TwoFAVerifyRequest(BaseModel):
    """Verify TOTP code to complete 2FA setup."""

    code: str
