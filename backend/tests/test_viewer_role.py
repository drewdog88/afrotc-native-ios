"""The read-only ``viewer`` role: can see everything, cannot mutate.

Every create/edit/delete on recruiting data is gated by ``require_write``,
which lets admins and recruiters through and returns 403 for viewers. Reads
and a viewer's own account actions (login, password change) stay open.
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models import User
from app.models.enums import UserRole


def _token(login: Callable[..., object], client: TestClient, username: str, password: str) -> str:
    resp = login(client, username, password)
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _viewer_headers(
    client: TestClient, make_user: Callable[..., User], login: Callable[..., object]
) -> dict[str, str]:
    make_user("viewer1", "Viewer123!", role=UserRole.VIEWER)
    return {"Authorization": f"Bearer {_token(login, client, 'viewer1', 'Viewer123!')}"}


def test_viewer_can_read(client, make_user, login):
    headers = _viewer_headers(client, make_user, login)
    for path in ("/api/v1/recruits", "/api/v1/cadets", "/api/v1/contacts", "/api/v1/events"):
        resp = client.get(path, headers=headers)
        assert resp.status_code == 200, f"{path}: {resp.text}"


def test_viewer_cannot_create(client, make_user, login):
    headers = _viewer_headers(client, make_user, login)
    resp = client.post("/api/v1/recruits", headers=headers, json={
        "first_name": "Sky", "last_name": "Ranger", "email": "sky@example.com",
    })
    assert resp.status_code == 403
    assert "read-only" in resp.json()["detail"].lower()


def test_viewer_cannot_edit_or_delete(client, make_user, login):
    # require_write runs before the handler, so the 403 lands even for a
    # nonexistent id (no 404 leak of whether the record exists).
    headers = _viewer_headers(client, make_user, login)
    patched = client.patch("/api/v1/recruits/1", headers=headers, json={"first_name": "X"})
    assert patched.status_code == 403
    assert client.delete("/api/v1/recruits/1", headers=headers).status_code == 403
    staged = client.post(
        "/api/v1/recruits/1/stage", headers=headers, json={"to_stage": "contacted"}
    )
    assert staged.status_code == 403


def test_viewer_blocked_across_all_entities(client, make_user, login):
    headers = _viewer_headers(client, make_user, login)
    cases = {
        "/api/v1/cadets": {"first_name": "A", "last_name": "B"},
        "/api/v1/contacts": {"university_name": "U", "contact_name": "C"},
        "/api/v1/events": {"title": "T", "event_type": "visit"},
        "/api/v1/followups": {"title": "T", "due_date": "2026-01-01"},
        "/api/v1/materials/links": {"title": "T", "url": "https://example.com"},
    }
    for path, payload in cases.items():
        assert client.post(path, headers=headers, json=payload).status_code == 403, path


def test_viewer_can_change_own_password(client, make_user, login):
    # Account self-service is not gated by require_write.
    headers = _viewer_headers(client, make_user, login)
    resp = client.post("/api/v1/auth/change-password", headers=headers, json={
        "current_password": "Viewer123!", "new_password": "Viewer456!",
    })
    assert resp.status_code == 200, resp.text


def test_recruiter_still_has_write(client, make_user, login):
    # Sanity: the gate does not block recruiters.
    make_user("rec1", "Recruit123!", role=UserRole.RECRUITER)
    headers = {"Authorization": f"Bearer {_token(login, client, 'rec1', 'Recruit123!')}"}
    resp = client.post("/api/v1/recruits", headers=headers, json={
        "first_name": "Sky", "last_name": "Ranger", "email": "sky2@example.com",
        "current_school": "Seattle Prep",
    })
    assert resp.status_code == 201, resp.text
