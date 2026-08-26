"""Profile + 2FA schemas."""

from __future__ import annotations

from datetime import datetime

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


class TrustedDeviceOut(ORMModel):
    """A trusted device that can skip 2FA until it expires or is revoked."""

    id: int
    device_label: str
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime


class RevokeOthersRequest(BaseModel):
    """Optional body for revoke-others, for cookieless (web) clients."""

    trust_token: str | None = None


class SessionOut(BaseModel):
    """An active signed-in device/session. `sid` is intentionally never exposed."""

    id: int
    device_label: str
    ip_address: str | None = None
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    current: bool = False
