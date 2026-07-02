"""UniversityContact schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.common import ORMModel


class ContactBase(BaseModel):
    university_name: str
    contact_name: str
    contact_title: str | None = None
    email: EmailStr
    phone: str | None = None
    address: str | None = None
    notes: str | None = None
    is_active: bool = True
    latitude: float | None = None
    longitude: float | None = None


class ContactCreate(ContactBase):
    pass


class ContactUpdate(BaseModel):
    university_name: str | None = None
    contact_name: str | None = None
    contact_title: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    notes: str | None = None
    is_active: bool | None = None
    latitude: float | None = None
    longitude: float | None = None


class ContactOut(ORMModel):
    id: int
    university_name: str
    contact_name: str
    contact_title: str | None = None
    # Plain str on output (input schemas validate as EmailStr).
    email: str
    phone: str | None = None
    address: str | None = None
    notes: str | None = None
    is_active: bool
    latitude: float | None = None
    longitude: float | None = None
    created_at: datetime | None = None
    last_modified: datetime | None = None
