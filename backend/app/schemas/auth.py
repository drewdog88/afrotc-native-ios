"""Auth + user schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    username: str  # accepts username or email
    password: str
    totp_code: str | None = None  # legacy; unused by the email flow, kept for compat
    trust_token: str | None = None  # opaque trusted-device token (also read from cookie)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    force_password_change: bool = False


class LoginResponse(BaseModel):
    """Either a token pair (success) or a 2FA challenge that needs a code."""

    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    force_password_change: bool = False
    two_factor_required: bool = False
    method: str | None = None
    challenge_token: str | None = None


class LoginVerifyRequest(BaseModel):
    challenge_token: str
    code: str
    trust_device: bool = False


class LoginVerifyResponse(TokenPair):
    trust_token: str | None = None


class ResendRequest(BaseModel):
    challenge_token: str


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    username: str  # accepts username or email


class SecretQuestionOut(BaseModel):
    secret_question: str


class ResetPasswordRequest(BaseModel):
    username: str  # accepts username or email
    secret_answer: str
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
    is_locked: bool
    is_admin: bool
    force_password_change: bool
    is_2fa_active: bool
    days_until_password_expiry: int | None = None
    created_at: datetime | None = None
