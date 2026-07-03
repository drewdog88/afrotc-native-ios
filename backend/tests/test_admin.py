"""Admin router: the admin gate and the last-admin deletion guardrail."""
from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models import User


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_recruiter_cannot_reach_admin(
    client: TestClient, make_user: Callable[..., User], login
) -> None:
    make_user("grunt")
    token = login(client, "grunt", "Recruit123!").json()["access_token"]
    assert client.get("/api/v1/admin/users", headers=_bearer(token)).status_code == 403


def test_admin_lists_users(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/admin/users", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1  # just the seeded admin


def test_admin_creates_user_forcing_password_change(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/api/v1/admin/users",
        headers=auth_headers,
        json={
            "username": "newrecruiter",
            "email": "newrecruiter@example.com",
            "password": "TempPass123!",
            "first_name": "New",
            "last_name": "Recruiter",
            "secret_question": "Mascot?",
            "secret_answer": "eagle",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["force_password_change"] is True
    assert body["role"] == "recruiter"


def test_cannot_delete_the_last_admin(
    client: TestClient, admin_user: User, auth_headers: dict[str, str]
) -> None:
    resp = client.delete(f"/api/v1/admin/users/{admin_user.id}", headers=auth_headers)
    assert resp.status_code == 400
    assert "last admin" in resp.json()["detail"].lower()


def test_can_delete_a_non_admin_user(
    client: TestClient, auth_headers: dict[str, str], make_user: Callable[..., User]
) -> None:
    victim = make_user("expendable")
    resp = client.delete(f"/api/v1/admin/users/{victim.id}", headers=auth_headers)
    assert resp.status_code == 204
