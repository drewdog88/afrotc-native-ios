"""Public request-info intake schemas."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, field_validator

from app.models.enums import GradeLevel, IntendedTerm


class IntakeCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    current_school: str
    grade_level: GradeLevel
    intended_entry_term: IntendedTerm
    intended_entry_year: int
    consent: bool
    turnstile_token: str = ""

    @field_validator("consent")
    @classmethod
    def _must_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Consent to be contacted is required.")
        return v

    @field_validator("intended_entry_year")
    @classmethod
    def _reasonable_year(cls, v: int) -> int:
        if v < 2000 or v > 2100:
            raise ValueError("Enter a valid year.")
        return v


class IntakeSubmitResult(BaseModel):
    ok: bool = True
    message: str = "Thanks! A recruiter will be in touch soon."


class _Option(BaseModel):
    value: str
    label: str


class IntakeOptions(BaseModel):
    grade_levels: list[_Option]
    terms: list[_Option]
