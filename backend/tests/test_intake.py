"""Public intake form: model shape, submission, spam gate, email best-effort."""
from __future__ import annotations

from app.models import IntakeSettings, PotentialRecruit
from app.models.enums import GradeLevel, IntendedTerm, SchoolType, school_type_for_grade


def test_new_recruit_columns_exist() -> None:
    r = PotentialRecruit(
        first_name="Pat", last_name="Cadet", current_school="Lincoln HS",
        grade_level=GradeLevel.HS_11.value, intended_entry_term=IntendedTerm.FALL.value,
        intended_entry_year=2027, source="public_intake_form", source_ip="203.0.113.7",
    )
    assert r.source == "public_intake_form"
    assert r.acknowledgment_email_sent_at is None


def test_intake_settings_defaults() -> None:
    s = IntakeSettings()
    assert s.recruiter_notification_email is None


def test_school_type_derivation() -> None:
    assert school_type_for_grade(GradeLevel.HS_11) == SchoolType.HIGH_SCHOOL
    assert school_type_for_grade(GradeLevel.COLLEGE_JUNIOR) == SchoolType.COLLEGE
    assert school_type_for_grade(GradeLevel.OTHER) == SchoolType.OTHER
