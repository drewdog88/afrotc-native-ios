"""PotentialRecruit + stage-event schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.enums import RecruitStage, SchoolType
from app.schemas.common import ORMModel


class RecruitBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr | None = None
    phone: str | None = None
    major: str | None = None
    current_school: str
    school_type: SchoolType = SchoolType.HIGH_SCHOOL
    high_school_graduation_year: int | None = None
    expected_college_graduation_year: int | None = None
    gpa: float | None = None
    sat_score: int | None = None
    act_score: int | None = None
    interests: str | None = None
    notes: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class RecruitCreate(RecruitBase):
    stage: RecruitStage = RecruitStage.LEAD


class RecruitUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    major: str | None = None
    current_school: str | None = None
    school_type: SchoolType | None = None
    high_school_graduation_year: int | None = None
    expected_college_graduation_year: int | None = None
    gpa: float | None = None
    sat_score: int | None = None
    act_score: int | None = None
    interests: str | None = None
    notes: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class RecruitOut(ORMModel):
    id: int
    first_name: str
    last_name: str
    full_name: str
    # Plain str on output (input schemas validate as EmailStr).
    email: str | None = None
    phone: str | None = None
    major: str | None = None
    current_school: str
    school_type: str
    high_school_graduation_year: int | None = None
    expected_college_graduation_year: int | None = None
    gpa: float | None = None
    sat_score: int | None = None
    act_score: int | None = None
    interests: str | None = None
    notes: str | None = None
    stage: str
    latitude: float | None = None
    longitude: float | None = None
    created_at: datetime | None = None
    last_modified: datetime | None = None


class StageChange(BaseModel):
    to_stage: RecruitStage
    note: str | None = None


class StageEventOut(ORMModel):
    id: int
    recruit_id: int
    from_stage: str | None = None
    to_stage: str
    changed_at: datetime
    changed_by_id: int | None = None
    note: str | None = None
