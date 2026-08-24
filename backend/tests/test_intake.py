"""Public intake form: model shape, submission, spam gate, email best-effort."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import settings
from app.models import IntakeSettings, PotentialRecruit
from app.models.enums import GradeLevel, IntendedTerm, SchoolType, school_type_for_grade
from app.services.email import build_recruiter_notification, render_ack
from tests.conftest import TestingSessionLocal


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
    r.id = 42
    subject, body = build_recruiter_notification(r)
    assert "Sam Lee" in body
    assert "sam@example.com" in body
    assert "Grant HS" in body
    # Direct deep link to this specific lead's detail page (not a generic reminder).
    assert f"{settings.site_url.rstrip('/')}/recruits/42" in body


def test_build_recruiter_notification_falls_back_when_no_id() -> None:
    from app.models import PotentialRecruit
    r = PotentialRecruit(first_name="Sam", last_name="Lee", current_school="Grant HS")
    _, body = build_recruiter_notification(r)
    # No id yet → link the recruits area rather than /recruits/None.
    assert f"{settings.site_url.rstrip('/')}/recruits" in body
    assert "/recruits/None" not in body


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


_VALID = {
    "first_name": "Jamie", "last_name": "Rivera", "email": "jamie@example.com",
    "phone": "503-555-0142", "current_school": "Cleveland HS", "grade_level": "hs_11",
    "intended_entry_term": "fall", "intended_entry_year": 2027, "consent": True,
    "turnstile_token": "test",
}


def _emails(monkeypatch):
    """Capture email sends without hitting the network."""
    sent = []
    import app.api.v1.intake as intake_mod

    def _fake_send(to, subject, body):
        sent.append(to)
        return True

    monkeypatch.setattr(intake_mod, "send_email", _fake_send)
    return sent


def test_options_are_public(client: TestClient) -> None:
    resp = client.get("/api/v1/intake/options")
    assert resp.status_code == 200
    body = resp.json()
    assert any(o["value"] == "hs_11" for o in body["grade_levels"])
    assert {o["value"] for o in body["terms"]} == {"fall", "spring"}


def test_valid_submission_creates_lead_and_sends_both_emails(client, monkeypatch) -> None:
    # Configure a recruiter address so the notification email is attempted.
    with TestingSessionLocal() as db:
        from app.bootstrap import bootstrap_intake_settings
        from app.models import IntakeSettings
        bootstrap_intake_settings(db)
        db.get(IntakeSettings, 1).recruiter_notification_email = "recruiter@det695.local"
        db.commit()
    sent = _emails(monkeypatch)
    resp = client.post("/api/v1/intake", json=_VALID)
    assert resp.status_code == 201, resp.text
    assert resp.json()["ok"] is True
    with TestingSessionLocal() as db:
        rows = db.query(PotentialRecruit).all()
        assert len(rows) == 1
        assert rows[0].stage == "lead"
        assert rows[0].source == "public_intake_form"
        assert rows[0].school_type == "high_school"
        assert rows[0].consent_given_at is not None
        assert rows[0].acknowledgment_email_sent_at is not None
    assert "jamie@example.com" in sent          # applicant ack
    assert "recruiter@det695.local" in sent      # recruiter notification


def test_missing_consent_is_422(client, monkeypatch) -> None:
    _emails(monkeypatch)
    bad = {**_VALID, "consent": False}
    assert client.post("/api/v1/intake", json=bad).status_code == 422


def test_failed_turnstile_is_400_and_no_row(client, monkeypatch) -> None:
    import app.api.v1.intake as intake_mod
    monkeypatch.setattr(intake_mod, "verify_turnstile", lambda token, ip: False)
    resp = client.post("/api/v1/intake", json=_VALID)
    assert resp.status_code == 400
    with TestingSessionLocal() as db:
        assert db.query(PotentialRecruit).count() == 0


def test_email_failure_still_returns_201(client, monkeypatch) -> None:
    import app.api.v1.intake as intake_mod
    monkeypatch.setattr(intake_mod, "send_email", lambda to, subject, body: False)
    resp = client.post("/api/v1/intake", json=_VALID)
    assert resp.status_code == 201
    with TestingSessionLocal() as db:
        r = db.query(PotentialRecruit).one()
        assert r.acknowledgment_email_sent_at is None  # ack never confirmed


def test_other_grade_maps_to_other_school_type(client, monkeypatch) -> None:
    _emails(monkeypatch)
    resp = client.post("/api/v1/intake", json={**_VALID, "grade_level": "other"})
    assert resp.status_code == 201
    with TestingSessionLocal() as db:
        assert db.query(PotentialRecruit).one().school_type == "other"


def test_overlength_current_school_is_422_not_500(client, monkeypatch) -> None:
    _emails(monkeypatch)
    bad = {**_VALID, "current_school": "A" * 101}
    resp = client.post("/api/v1/intake", json=bad)
    assert resp.status_code == 422
    with TestingSessionLocal() as db:
        assert db.query(PotentialRecruit).count() == 0


def test_overlength_first_name_is_422_not_500(client, monkeypatch) -> None:
    _emails(monkeypatch)
    bad = {**_VALID, "first_name": "A" * 51}
    resp = client.post("/api/v1/intake", json=bad)
    assert resp.status_code == 422
    with TestingSessionLocal() as db:
        assert db.query(PotentialRecruit).count() == 0


def test_ack_timestamp_commit_failure_still_returns_201(client, monkeypatch) -> None:
    # The lead-creation commit (source of truth) already succeeded by the time we
    # get here; a failure while stamping/committing the best-effort ack timestamp
    # must never fail the accepted submission (module docstring contract).
    import app.api.v1.intake as intake_mod
    from app.core.security import now_utc as real_now_utc

    _emails(monkeypatch)  # send_email succeeds, so we reach the ack-stamp branch

    calls = {"n": 0}

    def _flaky_now_utc():
        calls["n"] += 1
        if calls["n"] == 2:  # 1st call = consent_given_at, 2nd = ack timestamp
            raise RuntimeError("boom")
        return real_now_utc()

    monkeypatch.setattr(intake_mod, "now_utc", _flaky_now_utc)
    resp = client.post("/api/v1/intake", json=_VALID)
    assert resp.status_code == 201, resp.text
    assert resp.json()["ok"] is True
    with TestingSessionLocal() as db:
        r = db.query(PotentialRecruit).one()
        assert r.acknowledgment_email_sent_at is None  # ack-stamp commit never landed


def test_overlength_email_is_422(client, monkeypatch) -> None:
    # Confirms pydantic enforces max_length on EmailStr (verified directly in dev too).
    _emails(monkeypatch)
    bad = {**_VALID, "email": ("a" * 115) + "@example.com"}
    resp = client.post("/api/v1/intake", json=bad)
    assert resp.status_code == 422


def test_submission_writes_activity_log_entry(client, monkeypatch) -> None:
    # A public submission appears in the admin Activity Log with no user_id,
    # a "Public form" label, and both email outcomes in the details.
    from app.bootstrap import bootstrap_intake_settings
    from app.models import ActivityLog

    with TestingSessionLocal() as db:
        bootstrap_intake_settings(db)
        db.get(IntakeSettings, 1).recruiter_notification_email = "recruiter@det695.local"
        db.commit()
    _emails(monkeypatch)  # both sends succeed

    resp = client.post("/api/v1/intake", json=_VALID)
    assert resp.status_code == 201, resp.text

    with TestingSessionLocal() as db:
        entries = (
            db.query(ActivityLog).filter(ActivityLog.action == "CONTACT_SUBMITTED").all()
        )
        assert len(entries) == 1
        entry = entries[0]
        assert entry.user_id is None
        assert entry.username == "Public form"
        assert entry.table_name == "potential_recruit"
        assert entry.record_id is not None
        assert "recruiter notification: sent" in (entry.details or "")
        assert "acknowledgment: sent" in (entry.details or "")


def test_submission_activity_log_records_email_failure(client, monkeypatch) -> None:
    # No recruiter address configured + a failing send: the audit entry records
    # both. The submission itself still succeeds (201).
    import app.api.v1.intake as intake_mod
    from app.models import ActivityLog

    monkeypatch.setattr(intake_mod, "send_email", lambda to, subject, body: False)
    resp = client.post("/api/v1/intake", json=_VALID)
    assert resp.status_code == 201, resp.text

    with TestingSessionLocal() as db:
        entry = (
            db.query(ActivityLog).filter(ActivityLog.action == "CONTACT_SUBMITTED").one()
        )
        assert "recruiter notification: not configured" in (entry.details or "")
        assert "acknowledgment: failed" in (entry.details or "")
