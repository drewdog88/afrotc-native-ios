"""Cadet schemas."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, EmailStr

from app.schemas.common import ORMModel


class CadetBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    major: str
    graduation_year: int
    cadet_rank: str
    hometown: str | None = None
    officer_interest: str | None = None
    gpa: float | None = None


class CadetCreate(CadetBase):
    status: str = "active"


class CadetUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    major: str | None = None
    graduation_year: int | None = None
    cadet_rank: str | None = None
    hometown: str | None = None
    officer_interest: str | None = None
    status: str | None = None
    unenrollment_reason: str | None = None
    unenrollment_date: date | None = None
    gpa: float | None = None


class CadetOut(ORMModel):
    id: int
    first_name: str
    last_name: str
    full_name: str
    # Plain str on output (input schemas validate as EmailStr).
    email: str
    phone: str | None = None
    major: str
    graduation_year: int
    cadet_rank: str
    hometown: str | None = None
    officer_interest: str | None = None
    status: str
    unenrollment_reason: str | None = None
    unenrollment_date: date | None = None
    gpa: float | None = None
    created_at: datetime | None = None
    last_modified: datetime | None = None
