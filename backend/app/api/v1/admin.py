"""Admin endpoints: user management + activity log (admin-only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import Pagination, pagination, require_admin
from app.core.database import get_db
from app.core.security import hash_password
from app.models import ActivityLog, User
from app.models.enums import UserRole
from app.schemas.admin import ActivityLogOut, AdminUserCreate, AdminUserUpdate
from app.schemas.auth import UserOut
from app.schemas.common import Page
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
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    data = body.model_dump(exclude={"secret_answer"})
    data["password_hash"] = hash_password(body.password)
    data["secret_answer_hash"] = hash_password(body.secret_answer)
    data["force_password_change"] = True
    # Remove password from dict since we've converted it to password_hash
    data.pop("password", None)
    return crud.create(db, data)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: AdminUserUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    user = _get_or_404(db, user_id)
    data = body.model_dump(exclude_unset=True)

    # Hash password if provided
    if "password" in data and data["password"] is not None:
        data["password_hash"] = hash_password(data.pop("password"))

    return crud.update(db, user, data)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    _: User = Depends(require_admin),
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

    crud.delete(db, user)


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
