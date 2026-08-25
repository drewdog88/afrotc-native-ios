"""Auth: login, token gating, refresh, lockout, password policy, and TOTP."""
from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.core.config import settings
from app.models import User

from .conftest import ADMIN_PASSWORD, ADMIN_USERNAME


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_success_returns_token_pair(client: TestClient, admin_user: User, login) -> None:
    resp = login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"
    # Admin we seed has force_password_change=False and is expiry-exempt.
    assert body["force_password_change"] is False


def test_login_by_email_is_accepted(client: TestClient, admin_user: User, login) -> None:
    resp = login(client, "admin@det695.local", ADMIN_PASSWORD)
    assert resp.status_code == 200, resp.text


def test_login_wrong_password_is_401(client: TestClient, admin_user: User, login) -> None:
    resp = login(client, "admin", "wrong-password")
    assert resp.status_code == 401


def test_login_unknown_user_is_401(client: TestClient, login) -> None:
    resp = login(client, "ghost", "whatever")
    assert resp.status_code == 401


def test_me_requires_a_token(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_returns_current_user(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "admin"
    assert body["is_admin"] is True


def test_refresh_yields_a_usable_access_token(
    client: TestClient, admin_user: User, login
) -> None:
    tokens = login(client, ADMIN_USERNAME, ADMIN_PASSWORD).json()
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    new_access = resp.json()["access_token"]
    assert client.get("/api/v1/auth/me", headers=_bearer(new_access)).status_code == 200


def test_refresh_rejects_an_access_token(
    client: TestClient, admin_user: User, login
) -> None:
    # Passing an access token where a refresh token is expected must fail.
    access = login(client, ADMIN_USERNAME, ADMIN_PASSWORD).json()["access_token"]
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert resp.status_code == 401


def test_failed_logins_lock_the_account(
    client: TestClient, make_user: Callable[..., User], login
) -> None:
    make_user("locke")
    for _ in range(settings.max_failed_logins):
        assert login(client, "locke", "nope").status_code == 401
    # Even the correct password is now refused with a lockout 403.
    resp = login(client, "locke", "Recruit123!")
    assert resp.status_code == 403
    assert "locked" in resp.json()["detail"].lower()


def test_disabled_account_cannot_log_in(
    client: TestClient, make_user: Callable[..., User], login
) -> None:
    make_user("dormant", is_active=False)
    resp = login(client, "dormant", "Recruit123!")
    assert resp.status_code == 403


def test_change_password_flow(
    client: TestClient, make_user: Callable[..., User], login
) -> None:
    make_user("changer", "OldPass123!")
    token = login(client, "changer", "OldPass123!").json()["access_token"]
    headers = _bearer(token)

    # Wrong current password.
    resp = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "incorrect", "new_password": "BrandNew123!"},
    )
    assert resp.status_code == 400

    # New must differ from current.
    resp = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "OldPass123!", "new_password": "OldPass123!"},
    )
    assert resp.status_code == 400

    # Happy path.
    resp = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "OldPass123!", "new_password": "BrandNew123!"},
    )
    assert resp.status_code == 200

    # Old password no longer works; new one does.
    assert login(client, "changer", "OldPass123!").status_code == 401
    assert login(client, "changer", "BrandNew123!").status_code == 200


def test_change_password_blocks_history_reuse(
    client: TestClient, make_user: Callable[..., User], login
) -> None:
    make_user("recycler", "FirstPass123!")
    token = login(client, "recycler", "FirstPass123!").json()["access_token"]
    headers = _bearer(token)

    # Move off the original password.
    assert (
        client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            json={"current_password": "FirstPass123!", "new_password": "SecondPass123!"},
        ).status_code
        == 200
    )
    # Re-login with the new password, then try to reuse the original.
    token = login(client, "recycler", "SecondPass123!").json()["access_token"]
    resp = client.post(
        "/api/v1/auth/change-password",
        headers=_bearer(token),
        json={"current_password": "SecondPass123!", "new_password": "FirstPass123!"},
    )
    assert resp.status_code == 400
    assert "used" in resp.json()["detail"].lower()


def test_change_password_enforces_min_length(
    client: TestClient, make_user: Callable[..., User], login
) -> None:
    make_user("shorty", "LongEnough123!")
    token = login(client, "shorty", "LongEnough123!").json()["access_token"]
    resp = client.post(
        "/api/v1/auth/change-password",
        headers=_bearer(token),
        json={"current_password": "LongEnough123!", "new_password": "short"},
    )
    assert resp.status_code == 422  # schema rejects < 8 chars before the handler runs
