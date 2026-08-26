"""Admin endpoints: user management + activity log (admin-only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import Pagination, pagination, require_admin
from app.bootstrap import bootstrap_intake_settings
from app.core.database import get_db
from app.core.security import hash_password
from app.models import ActivityLog, IntakeSettings, User
from app.models.enums import UserRole
from app.schemas.admin import ActivityLogOut, AdminUserCreate, AdminUserUpdate
from app.schemas.auth import UserOut
from app.schemas.common import Message, Page
from app.schemas.intake import IntakeSettingsOut, IntakeSettingsUpdate
from app.services import otp, sessions, trusted_devices
from app.services.activity import record_activity
from app.services.crud import CRUDBase

router = APIRouter(prefix="/admin", tags=["admin"])

crud = CRUDBase(User)

_SEARCH_FIELDS = ("username", "email", "first_name", "last_name")


def _get_or_404(db: Session, user_id: int) -> User:
    user = crud.get(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.get("/users", response_model=Page[UserOut])
def list_users(
    page: Pagination = Depends(pagination),
    search: str | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Page[UserOut]:
    rows, total = crud.list(
        db,
        skip=page.skip,
        limit=page.limit,
        search=search,
        search_fields=_SEARCH_FIELDS,
    )
    return Page(items=rows, total=total, skip=page.skip, limit=page.limit)


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: AdminUserCreate,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    data = body.model_dump(exclude={"secret_answer"})
    data["password_hash"] = hash_password(body.password)
    data["secret_answer_hash"] = hash_password(body.secret_answer)
    data["force_password_change"] = True
    # Remove password from dict since we've converted it to password_hash
    data.pop("password", None)
    created = crud.create(db, data)
    record_activity(
        db,
        user=actor,
        action="CREATE",
        table_name="users",
        record_id=created.id,
        record_description=created.username,
        request=request,
    )
    return created


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: AdminUserUpdate,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    user = _get_or_404(db, user_id)
    data = body.model_dump(exclude_unset=True)
    changed_fields = sorted(data.keys())  # field names only — never values

    # 2FA is a derived toggle, not a raw column write.
    if "two_factor_enabled" in data:
        enable = data.pop("two_factor_enabled")
        if enable:
            user.two_factor_enabled = True
            user.two_factor_method = "email"
        else:
            user.two_factor_enabled = False
            user.two_factor_method = None
            otp.clear_code(user)
            trusted_devices.revoke_all(db, user)

    # Reject an email already taken by a different user (clean 409 instead of
    # a raw DB integrity error from the unique constraint).
    if data.get("email") is not None:
        data["email"] = str(data["email"])
        clash = db.scalar(
            select(User).where(User.email == data["email"], User.id != user.id)
        )
        if clash is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use by another user",
            )

    # Hash password if provided; an admin-set password is temporary, so force
    # the user to choose their own at next login.
    if data.get("password") is not None:
        data["password_hash"] = hash_password(data.pop("password"))
        data["force_password_change"] = True

    updated = crud.update(db, user, data)
    record_activity(
        db,
        user=actor,
        action="UPDATE",
        table_name="users",
        record_id=updated.id,
        record_description=updated.username,
        details="changed: " + ", ".join(changed_fields) if changed_fields else None,
        request=request,
    )
    return updated


@router.post("/users/{user_id}/revoke-trusted-devices", response_model=Message)
def admin_revoke_trusted_devices(
    user_id: int,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Message:
    user = _get_or_404(db, user_id)
    n = trusted_devices.revoke_all(db, user)
    record_activity(
        db, user=actor, action="UPDATE", table_name="users",
        record_id=user.id, record_description=user.username,
        details="revoked trusted devices", request=request,
    )
    return Message(detail=f"Revoked {n} device(s)")


@router.post("/users/{user_id}/revoke-sessions", response_model=Message)
def admin_revoke_sessions(
    user_id: int,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Message:
    user = _get_or_404(db, user_id)
    n = sessions.revoke_all(db, user)
    record_activity(
        db, user=actor, action="UPDATE", table_name="users",
        record_id=user.id, record_description=user.username,
        details="revoked sessions", request=request,
    )
    return Message(detail=f"Signed out {n} device(s)")


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    user = _get_or_404(db, user_id)

    # Block deleting the last admin
    admin_count = db.scalar(
        select(func.count()).select_from(User).where(User.role == UserRole.ADMIN.value)
    )
    if user.is_admin and admin_count == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last admin user",
        )

    # Capture identity before the row is gone.
    deleted_id, deleted_username = user.id, user.username
    crud.delete(db, user)
    record_activity(
        db,
        user=actor,
        action="DELETE",
        table_name="users",
        record_id=deleted_id,
        record_description=deleted_username,
        request=request,
    )


@router.get("/activity", response_model=Page[ActivityLogOut])
def list_activity(
    page: Pagination = Depends(pagination),
    user_id: int | None = Query(None),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Page[ActivityLogOut]:
    stmt = select(ActivityLog)

    if user_id is not None:
        stmt = stmt.where(ActivityLog.user_id == user_id)

    # Most recent first
    stmt = stmt.order_by(ActivityLog.created_at.desc())

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(db.scalars(stmt.offset(page.skip).limit(page.limit)).all())

    return Page(items=rows, total=total, skip=page.skip, limit=page.limit)


def _settings_row(db: Session) -> IntakeSettings:
    row = db.get(IntakeSettings, 1)
    if row is None:
        bootstrap_intake_settings(db)
        row = db.get(IntakeSettings, 1)
    return row


@router.get("/intake-settings", response_model=IntakeSettingsOut)
def get_intake_settings(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> IntakeSettings:
    return _settings_row(db)


@router.put("/intake-settings", response_model=IntakeSettingsOut)
def update_intake_settings(
    body: IntakeSettingsUpdate,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> IntakeSettings:
    row = _settings_row(db)
    data = body.model_dump(exclude_unset=True)
    changed_fields = sorted(data.keys())  # field names only — never values
    if "recruiter_notification_email" in data and data["recruiter_notification_email"] is not None:
        data["recruiter_notification_email"] = str(data["recruiter_notification_email"])
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    record_activity(
        db,
        user=actor,
        action="UPDATE",
        table_name="intake_settings",
        record_id=row.id,
        record_description="Request-Info settings",
        details="changed: " + ", ".join(changed_fields) if changed_fields else None,
        request=request,
    )
    return row
