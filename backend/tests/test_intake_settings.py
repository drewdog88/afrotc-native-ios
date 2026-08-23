"""Admin intake-settings endpoints + bootstrap seed."""
from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.bootstrap import bootstrap_intake_settings
from app.models import IntakeSettings, User
from tests.conftest import TestingSessionLocal


def test_bootstrap_seeds_single_settings_row() -> None:
    with TestingSessionLocal() as db:
        bootstrap_intake_settings(db)
        bootstrap_intake_settings(db)  # idempotent — second call is a no-op
        rows = db.query(IntakeSettings).all()
        assert len(rows) == 1
        assert rows[0].id == 1
        assert rows[0].ack_email_subject  # default is non-empty


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_get_intake_settings_admin_only(
    client: TestClient, make_user: Callable[..., User], login
) -> None:
    make_user("grunt")
    token = login(client, "grunt", "Recruit123!").json()["access_token"]
    assert client.get("/api/v1/admin/intake-settings", headers=_bearer(token)).status_code == 403


def test_admin_gets_and_updates_settings(client: TestClient, auth_headers: dict[str, str]) -> None:
    got = client.get("/api/v1/admin/intake-settings", headers=auth_headers)
    assert got.status_code == 200, got.text
    assert got.json()["ack_email_subject"]  # seeded default

    put = client.put(
        "/api/v1/admin/intake-settings",
        headers=auth_headers,
        json={"recruiter_notification_email": "lead@det695.org", "ack_email_subject": "Welcome!"},
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["recruiter_notification_email"] == "lead@det695.org"
    assert body["ack_email_subject"] == "Welcome!"
