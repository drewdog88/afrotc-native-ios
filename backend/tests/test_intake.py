"""Public intake form: model shape, submission, spam gate, email best-effort."""
from __future__ import annotations

from app.models import IntakeSettings, PotentialRecruit
from app.models.enums import GradeLevel, IntendedTerm, SchoolType, school_type_for_grade
from app.services.email import build_recruiter_notification, render_ack


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


def test_render_ack_substitutes_first_name() -> None:
    subject, body = render_ack("Hi {{first_name}}", "Hello {{first_name}}!", "Dana")
    assert subject == "Hi Dana"
    assert body == "Hello Dana!"


def test_render_ack_plain_text_is_not_html_escaped() -> None:
    # Plain text: whatever the applicant typed is inserted verbatim (no markup context).
    _, body = render_ack("s", "Hi {{first_name}}", "<b>x</b>")
    assert body == "Hi <b>x</b>"


def test_build_recruiter_notification_includes_key_fields() -> None:
    from app.models import PotentialRecruit
    r = PotentialRecruit(
        first_name="Sam", last_name="Lee", email="sam@example.com", phone="503-555-0100",
        current_school="Grant HS", grade_level="hs_12", intended_entry_term="fall",
        intended_entry_year=2027,
    )
    subject, body = build_recruiter_notification(r)
    assert "Sam Lee" in body
    assert "sam@example.com" in body
    assert "Grant HS" in body


def test_verify_turnstile_dev_mode_passes(monkeypatch) -> None:
    from app.core.config import settings
    from app.services import spam
    monkeypatch.setattr(settings, "turnstile_secret_key", "", raising=False)
    assert spam.verify_turnstile("anything", "203.0.113.1") is True


def test_client_ip_prefers_forwarded_for() -> None:
    from app.services.spam import client_ip

    class _Req:
        headers = {"x-forwarded-for": "198.51.100.9, 10.0.0.1"}
        class client:  # noqa: N801
            host = "10.0.0.1"

    assert client_ip(_Req()) == "198.51.100.9"
