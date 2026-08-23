"""Activity logging: auditable actions write ActivityLog rows (best-effort)."""
from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.models import User


def _activity(client: TestClient, headers: dict[str, str]) -> list[dict]:
    resp = client.get("/api/v1/admin/activity", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["items"]


def _recruit_body(**over: object) -> dict:
    body = {
        "first_name": "Test",
        "last_name": "Prospect",
        "current_school": "West HS",
        "school_type": "high_school",
        "stage": "lead",
    }
    body.update(over)
    return body


def test_login_is_logged(client: TestClient, auth_headers: dict[str, str]) -> None:
    # The auth_headers fixture already logged the admin in.
    logins = [i for i in _activity(client, auth_headers) if i["action"] == "LOGIN"]
    assert logins, "expected a LOGIN activity entry"
    assert logins[0]["table_name"] == "users"
    assert logins[0]["username"] == "admin"


def test_intake_settings_update_is_logged(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.put(
        "/api/v1/admin/intake-settings",
        headers=auth_headers,
        json={
            "recruiter_notification_email": "recruiter@example.com",
            "ack_email_subject": "Hi",
            "ack_email_body": "Body {{first_name}}",
        },
    )
    assert resp.status_code == 200, resp.text
    entries = [
        i
        for i in _activity(client, auth_headers)
        if i["table_name"] == "intake_settings" and i["action"] == "UPDATE"
    ]
    assert entries, "expected an intake_settings UPDATE entry"
    assert "recruiter_notification_email" in (entries[0]["details"] or "")


def test_user_management_is_logged(
    client: TestClient, auth_headers: dict[str, str], make_user: Callable[..., User]
) -> None:
    victim = make_user("expendable")
    assert (
        client.delete(f"/api/v1/admin/users/{victim.id}", headers=auth_headers).status_code
        == 204
    )
    deletes = [
        i
        for i in _activity(client, auth_headers)
        if i["table_name"] == "users" and i["action"] == "DELETE"
    ]
    assert deletes and deletes[0]["record_description"] == "expendable"


def test_recruit_create_and_stage_change_are_logged(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = client.post("/api/v1/recruits", headers=auth_headers, json=_recruit_body())
    assert created.status_code == 201, created.text
    rid = created.json()["id"]

    stage = client.post(
        f"/api/v1/recruits/{rid}/stage",
        headers=auth_headers,
        json={"to_stage": "contacted", "note": "reached out"},
    )
    assert stage.status_code == 200, stage.text

    items = _activity(client, auth_headers)
    creates = [
        i
        for i in items
        if i["table_name"] == "potential_recruit" and i["action"] == "CREATE"
    ]
    stages = [i for i in items if i["action"] == "STAGE_CHANGE"]
    assert creates and creates[0]["record_id"] == rid
    assert stages, "expected a STAGE_CHANGE entry"
    detail = stages[0]["details"] or ""
    assert "lead" in detail and "contacted" in detail


def test_logging_failure_does_not_break_the_action(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Force the audit write to blow up; the underlying create must still succeed.
    import app.services.activity as activity_mod

    def boom(*_a: object, **_k: object) -> None:
        raise RuntimeError("audit write failed")

    monkeypatch.setattr(activity_mod, "ActivityLog", boom)
    resp = client.post("/api/v1/recruits", headers=auth_headers, json=_recruit_body())
    assert resp.status_code == 201, resp.text
