"""FollowUp (task/reminder) CRUD + completion action."""
from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user, pagination
from app.core.database import get_db
from app.core.security import now_utc
from app.models import FollowUp, FollowUpStatus, User
from app.schemas.common import Page
from app.schemas.followup import FollowUpCreate, FollowUpOut, FollowUpUpdate
from app.services.crud import CRUDBase

router = APIRouter(prefix="/followups", tags=["followups"])

crud = CRUDBase(FollowUp)


def _get_or_404(db: Session, followup_id: int) -> FollowUp:
    followup = crud.get(db, followup_id)
    if followup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found")
    return followup


@router.get("", response_model=Page[FollowUpOut])
def list_followups(
    page: Pagination = Depends(pagination),
    assignee_id: str | None = Query(None),
    status_filter: FollowUpStatus | None = Query(None, alias="status"),
    due_before: date | datetime | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[FollowUpOut]:
    # Build filters dynamically.
    filters: dict[str, int | str | None] = {}

    # Handle assignee_id="me" literal or integer.
    if assignee_id is not None:
        if assignee_id.lower() == "me":
            filters["assignee_id"] = user.id
        else:
            try:
                filters["assignee_id"] = int(assignee_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="assignee_id must be an integer or 'me'",
                ) from None

    if status_filter is not None:
        filters["status"] = status_filter.value

    # Start with base query.
    stmt = select(FollowUp)
    for field, value in filters.items():
        if value is not None and hasattr(FollowUp, field):
            stmt = stmt.where(getattr(FollowUp, field) == value)

    # due_before filter.
    if due_before is not None:
        # Convert date to datetime if needed.
        if isinstance(due_before, date) and not isinstance(due_before, datetime):
            due_before = datetime.combine(due_before, datetime.min.time())
        stmt = stmt.where(FollowUp.due_date < due_before)

    # Count total.
    from sqlalchemy import func
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    # Apply ordering and pagination.
    stmt = stmt.order_by(FollowUp.due_date.asc()).offset(page.skip).limit(page.limit)
    rows = list(db.scalars(stmt).all())

    return Page(items=rows, total=total, skip=page.skip, limit=page.limit)


@router.get("/{followup_id}", response_model=FollowUpOut)
def get_followup(
    followup_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FollowUp:
    return _get_or_404(db, followup_id)


@router.post("", response_model=FollowUpOut, status_code=status.HTTP_201_CREATED)
def create_followup(
    body: FollowUpCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FollowUp:
    data = body.model_dump()
    data["created_by_id"] = user.id
    # Ensure status is stored as string value.
    if "status" in data and isinstance(data["status"], FollowUpStatus):
        data["status"] = data["status"].value
    return crud.create(db, data)


@router.patch("/{followup_id}", response_model=FollowUpOut)
def update_followup(
    followup_id: int,
    body: FollowUpUpdate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FollowUp:
    followup = _get_or_404(db, followup_id)
    data = body.model_dump(exclude_unset=True)
    # Convert enum to string if present.
    if "status" in data and isinstance(data["status"], FollowUpStatus):
        data["status"] = data["status"].value
    return crud.update(db, followup, data)


@router.delete("/{followup_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_followup(
    followup_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    followup = _get_or_404(db, followup_id)
    crud.delete(db, followup)


@router.post("/{followup_id}/complete", response_model=FollowUpOut)
def complete_followup(
    followup_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FollowUp:
    followup = _get_or_404(db, followup_id)
    if followup.status == FollowUpStatus.DONE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Follow-up is already completed",
        )
    followup.status = FollowUpStatus.DONE.value
    followup.completed_at = now_utc()
    db.commit()
    db.refresh(followup)
    return followup
