"""University/high-school contact CRUD.

Standard CRUD operations for maintaining recruitment relationships with
universities and high schools. Includes geographic coordinates for map views.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user, pagination
from app.core.database import get_db
from app.models import UniversityContact, User
from app.schemas.common import Page
from app.schemas.contact import ContactCreate, ContactOut, ContactUpdate
from app.services.crud import CRUDBase

router = APIRouter(prefix="/contacts", tags=["contacts"])

crud = CRUDBase(UniversityContact)

_SEARCH_FIELDS = ("university_name", "contact_name", "email", "address")


def _get_or_404(db: Session, contact_id: int) -> UniversityContact:
    contact = crud.get(db, contact_id)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )
    return contact


@router.get("", response_model=Page[ContactOut])
def list_contacts(
    page: Pagination = Depends(pagination),
    search: str | None = None,
    is_active: bool | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[ContactOut]:
    rows, total = crud.list(
        db,
        skip=page.skip,
        limit=page.limit,
        search=search,
        search_fields=_SEARCH_FIELDS,
        filters={"is_active": is_active},
    )
    return Page(items=rows, total=total, skip=page.skip, limit=page.limit)


@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(
    contact_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UniversityContact:
    return _get_or_404(db, contact_id)


@router.post("", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
def create_contact(
    body: ContactCreate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UniversityContact:
    return crud.create(db, body.model_dump())


@router.patch("/{contact_id}", response_model=ContactOut)
def update_contact(
    contact_id: int,
    body: ContactUpdate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UniversityContact:
    contact = _get_or_404(db, contact_id)
    return crud.update(db, contact, body.model_dump(exclude_unset=True))


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    contact = _get_or_404(db, contact_id)
    crud.delete(db, contact)
