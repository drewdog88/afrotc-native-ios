"""Profile + 2FA self-service lifecycle (any authenticated user)."""

from __future__ import annotations

import pyotp
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import decrypt_secret, encrypt_secret
from app.models import User
from app.schemas.auth import UserOut
from app.schemas.common import Message
from app.schemas.profile import (
    ProfileUpdate,
    TwoFASetupResponse,
    TwoFAStatus,
    TwoFAVerifyRequest,
)

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=UserOut)
def get_profile(user: User = Depends(get_current_user)) -> User:
    """Get current user profile."""
    return user


@router.patch("", response_model=UserOut)
def update_profile(
    body: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Update current user profile (self-service)."""
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


@router.get("/2fa", response_model=TwoFAStatus)
def get_2fa_status(user: User = Depends(get_current_user)) -> TwoFAStatus:
    """Check if 2FA is enabled for the current user."""
    return TwoFAStatus(enabled=user.totp_enabled and user.totp_setup_completed)


@router.post("/2fa/setup", response_model=TwoFASetupResponse)
def setup_2fa(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TwoFASetupResponse:
    """Initiate 2FA setup — generate secret and return provisioning URI."""
    if not user.can_enable_2fa:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="2FA setup not allowed for this account",
        )

    # Generate fresh TOTP secret
    secret = pyotp.random_base32()

    # Store encrypted, mark as pending verification
    user.totp_secret = encrypt_secret(secret)
    user.totp_enabled = False
    user.totp_setup_completed = False
    db.commit()

    # Return provisioning URI for QR code rendering on client
    totp = pyotp.TOTP(secret)
    otpauth_uri = totp.provisioning_uri(name=user.email, issuer_name="AFROTC Det 695")

    return TwoFASetupResponse(secret=secret, otpauth_uri=otpauth_uri)


@router.post("/2fa/verify", response_model=Message)
def verify_2fa(
    body: TwoFAVerifyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    """Verify TOTP code to complete 2FA setup."""
    if not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup not initiated. Call POST /profile/2fa/setup first.",
        )

    # Decrypt stored secret
    secret = decrypt_secret(user.totp_secret)
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt TOTP secret",
        )

    # Verify code with 1-window tolerance (±30s)
    totp = pyotp.TOTP(secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired 2FA code",
        )

    # Mark 2FA as fully enabled
    user.totp_enabled = True
    user.totp_setup_completed = True
    db.commit()

    return Message(detail="2FA enabled successfully")


@router.post("/2fa/disable", response_model=Message)
def disable_2fa(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    """Disable 2FA for the current user."""
    user.totp_secret = None
    user.totp_enabled = False
    user.totp_setup_completed = False
    db.commit()

    return Message(detail="2FA disabled successfully")
