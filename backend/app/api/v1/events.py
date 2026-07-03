"""Recruitment event CRUD.

This router manages recruitment events (school visits, fairs, etc.) following
the standard CRUDBase pattern established in recruits.py. Events can be linked
to university contacts and include geolocation for mapping.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user, pagination, require_write
from app.core.database import get_db
from app.models import RecruitmentEvent, User
from app.schemas.common import Page
from app.schemas.event import EventCreate, EventOut, EventUpdate
from app.services.crud import CRUDBase

router = APIRouter(prefix="/events", tags=["events"])

crud = CRUDBase(RecruitmentEvent)

_SEARCH_FIELDS = ("title", "location", "event_type", "description")


def _get_or_404(db: Session, event_id: int) -> RecruitmentEvent:
    event = crud.get(db, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.get("", response_model=Page[EventOut])
def list_events(
    page: Pagination = Depends(pagination),
    search: str | None = None,
    status: str | None = None,
    event_type: str | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[EventOut]:
    rows, total = crud.list(
        db,
        skip=page.skip,
        limit=page.limit,
        search=search,
        search_fields=_SEARCH_FIELDS,
        filters={"status": status, "event_type": event_type},
    )
    return Page(items=rows, total=total, skip=page.skip, limit=page.limit)


@router.get("/{event_id}", response_model=EventOut)
def get_event(
    event_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecruitmentEvent:
    return _get_or_404(db, event_id)


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(
    body: EventCreate,
    _: User = Depends(require_write),
    db: Session = Depends(get_db),
) -> RecruitmentEvent:
    return crud.create(db, body.model_dump())


@router.patch("/{event_id}", response_model=EventOut)
def update_event(
    event_id: int,
    body: EventUpdate,
    _: User = Depends(require_write),
    db: Session = Depends(get_db),
) -> RecruitmentEvent:
    event = _get_or_404(db, event_id)
    return crud.update(db, event, body.model_dump(exclude_unset=True))


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: int,
    _: User = Depends(require_write),
    db: Session = Depends(get_db),
) -> None:
    event = _get_or_404(db, event_id)
    crud.delete(db, event)
