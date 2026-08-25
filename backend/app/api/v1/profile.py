"""Profile + email 2FA self-service lifecycle (any authenticated user)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.auth import UserOut
from app.schemas.common import Message
from app.schemas.profile import (
    ProfileUpdate,
    TwoFAEnrollRequest,
    TwoFAStatus,
    TwoFAVerifyRequest,
)
from app.services import otp, trusted_devices
from app.services.email import send_2fa_code

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


@router.get("/2fa/status", response_model=TwoFAStatus)
def get_2fa_status(user: User = Depends(get_current_user)) -> TwoFAStatus:
    """Check 2FA enablement status for the current user."""
    return TwoFAStatus(
        enabled=user.is_2fa_active,
        method=user.two_factor_method,
        enrollment_prompted=user.two_factor_enrollment_prompted,
    )


@router.post("/2fa/enroll", response_model=Message)
def enroll_2fa(
    body: TwoFAEnrollRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    """Begin email 2FA enrollment — sends a verification code, does not activate."""
    if not user.can_enable_2fa:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="2FA not allowed for this account"
        )
    if body.method != "email":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported 2FA method"
        )
    code = otp.issue_code(user, "enroll")
    db.commit()
    send_2fa_code(user.email, code)
    return Message(detail="A verification code has been sent to your email")


@router.post("/2fa/enroll/verify", response_model=Message)
def verify_enroll_2fa(
    body: TwoFAVerifyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    """Verify the enrollment code and activate email 2FA."""
    if not otp.verify_code(user, body.code, "enroll"):
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code"
        )
    user.two_factor_enabled = True
    user.two_factor_method = "email"
    user.two_factor_enrollment_prompted = True
    db.commit()
    return Message(detail="Two-factor authentication enabled")


@router.post("/2fa/enrollment-dismiss", response_model=Message)
def dismiss_enrollment(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Message:
    """Mark the enrollment prompt as dismissed without enabling 2FA."""
    user.two_factor_enrollment_prompted = True
    db.commit()
    return Message(detail="Enrollment prompt dismissed")


@router.post("/2fa/disable", response_model=Message)
def disable_2fa(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Message:
    """Disable 2FA, clear any pending code, and revoke trusted devices."""
    user.two_factor_enabled = False
    user.two_factor_method = None
    otp.clear_code(user)
    trusted_devices.revoke_all(db, user)
    db.commit()
    return Message(detail="Two-factor authentication disabled")
