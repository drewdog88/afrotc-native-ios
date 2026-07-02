"""Cadet CRUD endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user, pagination
from app.core.database import get_db
from app.models import Cadet, User
from app.schemas.cadet import CadetCreate, CadetOut, CadetUpdate
from app.schemas.common import Page
from app.services.crud import CRUDBase

router = APIRouter(prefix="/cadets", tags=["cadets"])

crud = CRUDBase(Cadet)

_SEARCH_FIELDS = ("first_name", "last_name", "email", "major", "hometown")


def _get_or_404(db: Session, cadet_id: int) -> Cadet:
    cadet = crud.get(db, cadet_id)
    if cadet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cadet not found")
    return cadet


@router.get("", response_model=Page[CadetOut])
def list_cadets(
    page: Pagination = Depends(pagination),
    search: str | None = None,
    status: str | None = None,
    graduation_year: int | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[CadetOut]:
    rows, total = crud.list(
        db,
        skip=page.skip,
        limit=page.limit,
        search=search,
        search_fields=_SEARCH_FIELDS,
        filters={"status": status, "graduation_year": graduation_year},
    )
    return Page(items=rows, total=total, skip=page.skip, limit=page.limit)


@router.get("/{cadet_id}", response_model=CadetOut)
def get_cadet(
    cadet_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Cadet:
    return _get_or_404(db, cadet_id)


@router.post("", response_model=CadetOut, status_code=status.HTTP_201_CREATED)
def create_cadet(
    body: CadetCreate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Cadet:
    return crud.create(db, body.model_dump())


@router.patch("/{cadet_id}", response_model=CadetOut)
def update_cadet(
    cadet_id: int,
    body: CadetUpdate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Cadet:
    cadet = _get_or_404(db, cadet_id)
    return crud.update(db, cadet, body.model_dump(exclude_unset=True))


@router.delete("/{cadet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cadet(
    cadet_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    cadet = _get_or_404(db, cadet_id)
    crud.delete(db, cadet)
