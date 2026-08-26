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


def test_admin_edits_user_profile_fields(
    client: TestClient, auth_headers: dict[str, str], make_user: Callable[..., User]
) -> None:
    user = make_user("editme")
    resp = client.patch(
        f"/api/v1/admin/users/{user.id}",
        headers=auth_headers,
        json={
            "first_name": "Edited",
            "last_name": "Person",
            "email": "edited.person@example.com",
            "phone": "555-0100",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["first_name"] == "Edited"
    assert body["last_name"] == "Person"
    assert body["email"] == "edited.person@example.com"
    assert body["phone"] == "555-0100"


def test_admin_password_reset_forces_change_at_next_login(
    client: TestClient, auth_headers: dict[str, str], make_user: Callable[..., User]
) -> None:
    user = make_user("resetme", force_password_change=False)
    resp = client.patch(
        f"/api/v1/admin/users/{user.id}",
        headers=auth_headers,
        json={"password": "BrandNewPass123!"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["force_password_change"] is True


def test_admin_can_see_and_unlock_a_locked_user(
    client: TestClient, auth_headers: dict[str, str], make_user: Callable[..., User]
) -> None:
    from tests.conftest import TestingSessionLocal

    user = make_user("lockedout")
    # Simulate a lockout directly; the failed-login path isn't under test here.
    with TestingSessionLocal() as db:
        row = db.get(User, user.id)
        row.is_locked = True
        row.failed_login_attempts = 5
        db.commit()

    # The admin listing surfaces the locked state.
    listing = client.get("/api/v1/admin/users", headers=auth_headers).json()
    locked = next(u for u in listing["items"] if u["id"] == user.id)
    assert locked["is_locked"] is True

    # Unlocking clears the flag (and the attempt counter).
    resp = client.patch(
        f"/api/v1/admin/users/{user.id}",
        headers=auth_headers,
        json={"is_locked": False, "failed_login_attempts": 0},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_locked"] is False


def test_admin_edit_duplicate_email_returns_409(
    client: TestClient, auth_headers: dict[str, str], make_user: Callable[..., User]
) -> None:
    alice = make_user("alice")
    # Give alice a real (validatable) email so bob can collide with it.
    assert (
        client.patch(
            f"/api/v1/admin/users/{alice.id}",
            headers=auth_headers,
            json={"email": "shared@example.com"},
        ).status_code
        == 200
    )
    bob = make_user("bob")
    resp = client.patch(
        f"/api/v1/admin/users/{bob.id}",
        headers=auth_headers,
        json={"email": "shared@example.com"},
    )
    assert resp.status_code == 409, resp.text


def test_admin_revoke_sessions(client, admin_user, auth_headers, make_user):
    target = make_user("target", "Recruit123!")
    client.post("/api/v1/auth/login", json={"username": "target", "password": "Recruit123!"})
    r = client.post(f"/api/v1/admin/users/{target.id}/revoke-sessions", headers=auth_headers)
    assert r.status_code == 200
    assert "device" in r.json()["detail"]
