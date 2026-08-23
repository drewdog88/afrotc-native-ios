"""Public request-info intake schemas."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import GradeLevel, IntendedTerm
from app.schemas.common import ORMModel


class IntakeCreate(BaseModel):
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    email: EmailStr = Field(max_length=120)
    phone: str = Field(max_length=20)
    current_school: str = Field(max_length=100)
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


class IntakeSettingsOut(ORMModel):
    id: int
    recruiter_notification_email: str | None = None
    ack_email_subject: str
    ack_email_body: str


class IntakeSettingsUpdate(BaseModel):
    recruiter_notification_email: EmailStr | None = None
    ack_email_subject: str | None = None
    ack_email_body: str | None = None
