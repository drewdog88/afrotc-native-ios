"""Auth + user schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    username: str  # accepts username or email
    password: str
    totp_code: str | None = None  # required when the account has 2FA active


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    force_password_change: bool = False


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(ORMModel):
    id: int
    username: str
    # Plain str on output: stored values shouldn't fail serialization (e.g. the
    # internal `.local` bootstrap domain). Input schemas still validate as email.
    email: str
    first_name: str
    last_name: str
    full_name: str
    phone: str | None = None
    role: str
    is_active: bool
    is_admin: bool
    force_password_change: bool
    is_2fa_active: bool
    days_until_password_expiry: int | None = None
    created_at: datetime | None = None
