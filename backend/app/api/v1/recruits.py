"""Potential-recruit CRUD + funnel stage transitions.

This is the *reference* entity router: the CRUDBase pattern every other
entity router mirrors, plus the stage-change endpoint that appends an
immutable RecruitStageEvent. That append-only log is what /analytics/funnel
and /analytics/trends read — so recording a transition here is what makes the
"recruitment change over time" reporting possible. When a recruit is created,
we seed a baseline event (from_stage=None) so the funnel has a starting point.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user, pagination, require_write
from app.core.database import get_db
from app.models import PotentialRecruit, RecruitStageEvent, User
from app.schemas.common import Page
from app.schemas.recruit import (
    RecruitCreate,
    RecruitOut,
    RecruitUpdate,
    StageChange,
    StageEventOut,
)
from app.services.crud import CRUDBase

router = APIRouter(prefix="/recruits", tags=["recruits"])

crud = CRUDBase(PotentialRecruit)

_SEARCH_FIELDS = ("first_name", "last_name", "email", "current_school", "major")


def _get_or_404(db: Session, recruit_id: int) -> PotentialRecruit:
    recruit = crud.get(db, recruit_id)
    if recruit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recruit not found")
    return recruit


@router.get("", response_model=Page[RecruitOut])
def list_recruits(
    page: Pagination = Depends(pagination),
    search: str | None = None,
    stage: str | None = None,
    school_type: str | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[RecruitOut]:
    rows, total = crud.list(
        db,
        skip=page.skip,
        limit=page.limit,
        search=search,
        search_fields=_SEARCH_FIELDS,
        filters={"stage": stage, "school_type": school_type},
    )
    return Page(items=rows, total=total, skip=page.skip, limit=page.limit)


@router.get("/{recruit_id}", response_model=RecruitOut)
def get_recruit(
    recruit_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PotentialRecruit:
    return _get_or_404(db, recruit_id)


@router.post("", response_model=RecruitOut, status_code=status.HTTP_201_CREATED)
def create_recruit(
    body: RecruitCreate,
    user: User = Depends(require_write),
    db: Session = Depends(get_db),
) -> PotentialRecruit:
    recruit = crud.create(db, body.model_dump())
    # Seed the funnel with a baseline entry event so trends have a start point.
    db.add(
        RecruitStageEvent(
            recruit_id=recruit.id,
            from_stage=None,
            to_stage=recruit.stage,
            changed_by_id=user.id,
            note="Recruit created",
        )
    )
    db.commit()
    db.refresh(recruit)
    return recruit


@router.patch("/{recruit_id}", response_model=RecruitOut)
def update_recruit(
    recruit_id: int,
    body: RecruitUpdate,
    _: User = Depends(require_write),
    db: Session = Depends(get_db),
) -> PotentialRecruit:
    recruit = _get_or_404(db, recruit_id)
    return crud.update(db, recruit, body.model_dump(exclude_unset=True))


@router.delete("/{recruit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recruit(
    recruit_id: int,
    _: User = Depends(require_write),
    db: Session = Depends(get_db),
) -> None:
    recruit = _get_or_404(db, recruit_id)
    crud.delete(db, recruit)


@router.post("/{recruit_id}/stage", response_model=RecruitOut)
def change_stage(
    recruit_id: int,
    body: StageChange,
    user: User = Depends(require_write),
    db: Session = Depends(get_db),
) -> PotentialRecruit:
    recruit = _get_or_404(db, recruit_id)
    new_stage = body.to_stage.value
    if new_stage == recruit.stage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Recruit is already at stage '{new_stage}'",
        )
    db.add(
        RecruitStageEvent(
            recruit_id=recruit.id,
            from_stage=recruit.stage,
            to_stage=new_stage,
            changed_by_id=user.id,
            note=body.note,
        )
    )
    recruit.stage = new_stage
    db.commit()
    db.refresh(recruit)
    return recruit


@router.get("/{recruit_id}/stage-history", response_model=list[StageEventOut])
def stage_history(
    recruit_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RecruitStageEvent]:
    _get_or_404(db, recruit_id)
    return list(
        db.scalars(
            select(RecruitStageEvent)
            .where(RecruitStageEvent.recruit_id == recruit_id)
            .order_by(RecruitStageEvent.changed_at)
        ).all()
    )
