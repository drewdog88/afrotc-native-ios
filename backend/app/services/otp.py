"""Email one-time-code lifecycle, shared by enrollment and login challenges.

The pending code lives on the user row (hashed). Callers mutate the user and
commit through their own DB session; this module never commits.
"""
from __future__ import annotations

import secrets
from datetime import timedelta

from app.core import security
from app.core.config import settings
from app.models import User


def generate_code() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(settings.otp_code_length))


def _set_code(user: User, purpose: str) -> str:
    code = generate_code()
    user.otp_code_hash = security.hash_password(code)
    user.otp_expires_at = security.now_utc() + timedelta(minutes=settings.otp_ttl_minutes)
    user.otp_purpose = purpose
    user.otp_last_sent_at = security.now_utc()
    return code


def issue_code(user: User, purpose: str) -> str:
    """Start a fresh challenge for `purpose` (resets attempts + resend counters)."""
    user.otp_attempts = 0
    user.otp_resends = 0
    return _set_code(user, purpose)


def can_resend(user: User) -> bool:
    if user.otp_resends >= settings.otp_max_resends:
        return False
    if user.otp_last_sent_at is None:
        return True
    elapsed = (security.now_utc() - user.otp_last_sent_at).total_seconds()
    return elapsed >= settings.otp_resend_cooldown_seconds


def resend_code(user: User) -> str | None:
    """Issue a new code for the current purpose, or None if capped / cooling down.

    The running `otp_attempts` count is preserved across resends — a resend is
    part of the same challenge, so the verify-attempt budget must not reset.
    """
    if user.otp_code_hash is None or user.otp_purpose is None:
        return None
    if not can_resend(user):
        return None
    purpose = user.otp_purpose
    resends = user.otp_resends + 1
    code = _set_code(user, purpose)
    user.otp_resends = resends
    return code


def clear_code(user: User) -> None:
    user.otp_code_hash = None
    user.otp_expires_at = None
    user.otp_attempts = 0
    user.otp_resends = 0
    user.otp_purpose = None
    user.otp_last_sent_at = None


def verify_code(user: User, code: str, purpose: str) -> bool:
    if (
        user.otp_code_hash is None
        or user.otp_purpose != purpose
        or user.otp_expires_at is None
        or security.now_utc() > user.otp_expires_at
    ):
        return False
    if user.otp_attempts >= settings.otp_max_attempts:
        clear_code(user)
        return False
    if not security.verify_password(code, user.otp_code_hash):
        user.otp_attempts += 1
        if user.otp_attempts >= settings.otp_max_attempts:
            clear_code(user)
        return False
    clear_code(user)
    return True
