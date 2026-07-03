"""Authentication: login, refresh, me, change-password.

Carries forward the legacy password policy — failed-login lockout, password
history, expiry — but issues JWT access + refresh tokens instead of server
sessions. 2FA verification is enforced here when an account has it active;
the setup/disable lifecycle lives in the (workflow-built) profile router.
"""
from __future__ import annotations

from datetime import timedelta

import pyotp
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    decrypt_secret,
    hash_password,
    now_utc,
    verify_password,
)
from app.models import PasswordHistory, User
from app.schemas.auth import (
    AccessToken,
    ForgotPasswordRequest,
    LoginRequest,
    PasswordChange,
    RefreshRequest,
    ResetPasswordRequest,
    SecretQuestionOut,
    TokenPair,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_BAD_CREDS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
)


def _find_user(db: Session, identifier: str) -> User | None:
    return db.scalar(
        select(User).where(or_(User.username == identifier, User.email == identifier))
    )


def _reject_password_reuse(db: Session, user: User, new_password: str) -> None:
    """Raise 400 if the new password matches one retained in history."""
    recent = db.scalars(
        select(PasswordHistory)
        .where(PasswordHistory.user_id == user.id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(settings.password_history_size)
    ).all()
    if any(verify_password(new_password, h.password_hash) for h in recent):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password was used within the last {settings.password_history_size} changes",
        )


def _apply_new_password(db: Session, user: User, new_password: str) -> None:
    """Retire the current password to history and set the new one (no commit)."""
    db.add(PasswordHistory(user_id=user.id, password_hash=user.password_hash))
    user.password_hash = hash_password(new_password)
    user.password_changed_at = now_utc()
    user.force_password_change = False
    if not user.is_admin:
        user.password_expires_at = now_utc() + timedelta(days=settings.password_expiry_days)


@router.post("/login", response_model=TokenPair)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    user = _find_user(db, body.username)
    if user is None:
        raise _BAD_CREDS
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account locked due to failed logins. Contact an administrator.",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    if not verify_password(body.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_failed_logins:
            user.is_locked = True
        db.commit()
        raise _BAD_CREDS

    # Second factor, when the account has it active.
    if user.is_2fa_active:
        if not body.totp_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="2FA code required"
            )
        secret = decrypt_secret(user.totp_secret) if user.totp_secret else None
        if not secret or not pyotp.TOTP(secret).verify(body.totp_code, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid 2FA code"
            )

    # Success — reset counters.
    user.failed_login_attempts = 0
    db.commit()

    subject = str(user.id)
    return TokenPair(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
        force_password_change=user.force_password_change or user.is_password_expired,
    )


@router.post("/refresh", response_model=AccessToken)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> AccessToken:
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    return AccessToken(access_token=create_access_token(str(user.id)))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> None:
    # Stateless JWT: clients discard their tokens. Endpoint exists for symmetry
    # and so future token-revocation can hook in without a client change.
    return None


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/change-password", response_model=UserOut)
def change_password(
    body: PasswordChange,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
        )
    if verify_password(body.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from the current one",
        )

    _reject_password_reuse(db, user, body.new_password)
    _apply_new_password(db, user, body.new_password)
    db.commit()
    db.refresh(user)
    return user


@router.post("/forgot-password", response_model=SecretQuestionOut)
def forgot_password(
    body: ForgotPasswordRequest, db: Session = Depends(get_db)
) -> SecretQuestionOut:
    """Return the account's security question so the user can prove ownership.

    Recovery is self-service via the security question every account carries;
    there is no email dependency. A disabled account is treated as not found so
    an administrator's deliberate deactivation can't be undone this way.
    """
    user = _find_user(db, body.username)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found for that username or email",
        )
    return SecretQuestionOut(secret_question=user.secret_question)


@router.post("/reset-password", response_model=UserOut)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)) -> User:
    """Reset a password after verifying the account's security answer.

    A correct answer also clears any failed-login lockout so the user can sign
    in immediately. Wrong answers count toward the same lockout as failed
    logins, so the question can't be brute-forced.
    """
    user = _find_user(db, body.username)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to reset password. Check your details or contact an administrator.",
        )
    # Trim to mirror how the answer is captured at sign-up.
    if not verify_password(body.secret_answer.strip(), user.secret_answer_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_failed_logins:
            user.is_locked = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Security answer is incorrect"
        )

    _reject_password_reuse(db, user, body.new_password)
    _apply_new_password(db, user, body.new_password)
    # Recovery clears the lockout so the user can sign in right away.
    user.is_locked = False
    user.failed_login_attempts = 0
    db.commit()
    db.refresh(user)
    return user
