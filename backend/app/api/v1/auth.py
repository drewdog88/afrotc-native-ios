"""Authentication: login, refresh, me, change-password.

Carries forward the legacy password policy — failed-login lockout, password
history, expiry — but issues JWT access + refresh tokens instead of server
sessions. 2FA verification is enforced here when an account has it active;
the setup/disable lifecycle lives in the (workflow-built) profile router.
"""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_session, get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_challenge_token,
    create_refresh_token,
    decode_token,
    hash_password,
    now_utc,
    verify_password,
)
from app.models import AuthSession, PasswordHistory, User
from app.schemas.auth import (
    AccessToken,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    LoginVerifyRequest,
    LoginVerifyResponse,
    PasswordChange,
    RefreshRequest,
    ResendRequest,
    ResetPasswordRequest,
    SecretQuestionOut,
    UserOut,
)
from app.schemas.common import Message
from app.services import otp, sessions, throttle, trusted_devices
from app.services.activity import record_activity
from app.services.email import send_2fa_code

router = APIRouter(prefix="/auth", tags=["auth"])

_BAD_CREDS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
)

# A throwaway hash used only to equalize response timing when a username does
# not exist: verifying against it costs the same as a real password check, so
# "no such user" can't be distinguished from "wrong password" by latency. Not a
# secret — its only job is to burn the same bcrypt time.
_DUMMY_PASSWORD_HASH = hash_password("login-timing-equalizer")

# The refresh cookie is only ever sent to the auth routes, so scope it there
# rather than to the whole site. Browser clients rely on this httponly cookie
# instead of storing the refresh token in JS-readable localStorage; native
# clients (iOS) keep using the response/request body and simply ignore it.
_REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        max_age=settings.refresh_token_expire_days * 24 * 3600,
        httponly=True,
        secure=True,
        samesite="lax",
        path=_REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(settings.refresh_cookie_name, path=_REFRESH_COOKIE_PATH)


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


def _issue_token_pair(user: User, sid: str) -> tuple[str, str]:
    subject = str(user.id)
    claim = {"sid": sid}
    return create_access_token(subject, claim), create_refresh_token(subject, claim)


def _record_login(db: Session, user: User, request: Request) -> None:
    user.failed_login_attempts = 0
    db.commit()
    record_activity(
        db, user=user, action="LOGIN", table_name="users",
        record_id=user.id, record_description=user.username, request=request,
    )


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)
) -> LoginResponse:
    throttle.enforce(db, request, "login")
    user = _find_user(db, body.username)
    # Verify the password BEFORE disclosing any account state. Someone who does
    # not supply the correct password gets an identical generic 401 whether the
    # username is unknown, wrong, locked, or disabled — so /login can't be used
    # to enumerate accounts or their status. The dummy verify keeps the unknown-
    # username path the same cost as a real check (no timing oracle).
    if user is None:
        verify_password(body.password, _DUMMY_PASSWORD_HASH)
        raise _BAD_CREDS
    if not verify_password(body.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_failed_logins:
            user.is_locked = True
        db.commit()
        raise _BAD_CREDS

    # Password is correct — it is now safe to tell the real account owner why
    # they can't proceed (locked / disabled), since they've proven ownership.
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account locked due to failed logins. Contact an administrator.",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    if user.is_2fa_active:
        cookie_token = request.cookies.get(settings.trusted_device_cookie_name)
        if trusted_devices.find_valid(db, user, body.trust_token or cookie_token):
            _record_login(db, user, request)
            session = sessions.start(db, user, request)
            access, refresh = _issue_token_pair(user, session.sid)
            _set_refresh_cookie(response, refresh)
            return LoginResponse(
                access_token=access, refresh_token=refresh,
                force_password_change=user.force_password_change or user.is_password_expired,
            )
        # Email challenge: mint + store a code, email it, return a challenge token.
        code = otp.issue_code(user, "login")
        db.commit()
        send_2fa_code(user.email, code)
        return LoginResponse(
            two_factor_required=True,
            method=user.two_factor_method,
            challenge_token=create_challenge_token(str(user.id)),
        )

    _record_login(db, user, request)
    session = sessions.start(db, user, request)
    access, refresh = _issue_token_pair(user, session.sid)
    _set_refresh_cookie(response, refresh)
    return LoginResponse(
        access_token=access, refresh_token=refresh,
        force_password_change=user.force_password_change or user.is_password_expired,
    )


def _challenge_user(db: Session, challenge_token: str) -> User:
    payload = decode_token(challenge_token)
    if not payload or payload.get("type") != "login_2fa":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired challenge"
        )
    try:
        user = db.get(User, int(payload["sub"]))
    except (KeyError, ValueError, TypeError):
        user = None
    if user is None or not user.is_active or not user.is_2fa_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired challenge"
        )
    return user


@router.post("/login/verify", response_model=LoginVerifyResponse)
def login_verify(
    body: LoginVerifyRequest, request: Request, response: Response, db: Session = Depends(get_db)
) -> LoginVerifyResponse:
    user = _challenge_user(db, body.challenge_token)
    if not otp.verify_code(user, body.code, "login"):
        db.commit()  # persist the attempt increment
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired code"
        )

    _record_login(db, user, request)
    trust_token: str | None = None
    if body.trust_device:
        label = request.headers.get("user-agent", "")[:255]
        trust_token = trusted_devices.trust_device(db, user, label)
        response.set_cookie(
            key=settings.trusted_device_cookie_name,
            value=trust_token,
            max_age=settings.trusted_device_ttl_days * 24 * 3600,
            httponly=True, secure=True, samesite="lax",
        )
    session = sessions.start(db, user, request)
    access, refresh = _issue_token_pair(user, session.sid)
    _set_refresh_cookie(response, refresh)
    return LoginVerifyResponse(
        access_token=access, refresh_token=refresh,
        force_password_change=user.force_password_change or user.is_password_expired,
        trust_token=trust_token,
    )


@router.post("/login/resend", response_model=Message)
def login_resend(body: ResendRequest, db: Session = Depends(get_db)) -> Message:
    user = _challenge_user(db, body.challenge_token)
    if user.otp_purpose != "login":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No active login challenge"
        )
    code = otp.resend_code(user)
    if code is None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait before requesting another code",
        )
    db.commit()
    send_2fa_code(user.email, code)
    return Message(detail="A new code has been sent")


@router.post("/refresh", response_model=AccessToken)
def refresh(
    request: Request, db: Session = Depends(get_db), body: RefreshRequest | None = None
) -> AccessToken:
    # Browser clients send nothing in the body — the refresh token rides in the
    # httponly cookie. Native clients (iOS) still pass it in the body; the cookie
    # takes precedence when both are present.
    token = request.cookies.get(settings.refresh_cookie_name) or (
        body.refresh_token if body else None
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    session = sessions.get_valid(db, payload.get("sid"))
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    sessions.touch(db, session)
    return AccessToken(access_token=create_access_token(str(user.id), {"sid": session.sid}))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    session: AuthSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> None:
    session.revoked_at = now_utc()
    db.commit()
    _clear_refresh_cookie(response)
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
    trusted_devices.revoke_all(db, user)
    sessions.revoke_all(db, user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/forgot-password", response_model=SecretQuestionOut)
def forgot_password(
    body: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)
) -> SecretQuestionOut:
    """Return the account's security question so the user can prove ownership.

    Recovery is self-service via the security question every account carries;
    there is no email dependency. A disabled account is treated as not found so
    an administrator's deliberate deactivation can't be undone this way.
    """
    throttle.enforce(db, request, "forgot-password")
    user = _find_user(db, body.username)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found for that username or email",
        )
    return SecretQuestionOut(secret_question=user.secret_question)


@router.post("/reset-password", response_model=UserOut)
def reset_password(
    body: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)
) -> User:
    """Reset a password after verifying the account's security answer.

    A correct answer also clears any failed-login lockout so the user can sign
    in immediately. Wrong answers count toward the same lockout as failed
    logins, so the question can't be brute-forced.
    """
    throttle.enforce(db, request, "reset-password")
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
    trusted_devices.revoke_all(db, user)
    sessions.revoke_all(db, user)
    # Recovery clears the lockout so the user can sign in right away.
    user.is_locked = False
    user.failed_login_attempts = 0
    db.commit()
    db.refresh(user)
    return user
