"""Profile self-service + the 2FA (TOTP) enable/verify/disable lifecycle."""

from __future__ import annotations

from collections.abc import Callable

import pyotp
from fastapi.testclient import TestClient

from app.models import User


def test_profile_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/profile").status_code == 401


def test_get_and_update_profile(client: TestClient, auth_headers: dict[str, str]) -> None:
    me = client.get("/api/v1/profile", headers=auth_headers)
    assert me.status_code == 200
    assert me.json()["username"] == "admin"

    patched = client.patch(
        "/api/v1/profile",
        headers=auth_headers,
        json={"first_name": "Ada", "phone": "206-555-0142"},
    )
    assert patched.status_code == 200
    assert patched.json()["first_name"] == "Ada"
    assert patched.json()["phone"] == "206-555-0142"


def test_2fa_full_lifecycle(client: TestClient, auth_headers: dict[str, str]) -> None:
    # Starts disabled.
    assert client.get("/api/v1/profile/2fa", headers=auth_headers).json()["enabled"] is False

    # Setup returns a secret + provisioning URI, but 2FA is not yet on.
    setup = client.post("/api/v1/profile/2fa/setup", headers=auth_headers)
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    assert setup.json()["otpauth_uri"].startswith("otpauth://totp/")
    assert client.get("/api/v1/profile/2fa", headers=auth_headers).json()["enabled"] is False

    # Verifying a valid code completes setup.
    code = pyotp.TOTP(secret).now()
    verified = client.post("/api/v1/profile/2fa/verify", headers=auth_headers, json={"code": code})
    assert verified.status_code == 200
    assert client.get("/api/v1/profile/2fa", headers=auth_headers).json()["enabled"] is True

    # Disable turns it back off.
    disabled = client.post("/api/v1/profile/2fa/disable", headers=auth_headers)
    assert disabled.status_code == 200
    assert client.get("/api/v1/profile/2fa", headers=auth_headers).json()["enabled"] is False


def test_2fa_verify_before_setup_is_400(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.post("/api/v1/profile/2fa/verify", headers=auth_headers, json={"code": "000000"})
    assert resp.status_code == 400
    assert "setup not initiated" in resp.json()["detail"].lower()


def test_2fa_verify_wrong_code_is_400(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post("/api/v1/profile/2fa/setup", headers=auth_headers)
    resp = client.post("/api/v1/profile/2fa/verify", headers=auth_headers, json={"code": "123456"})
    assert resp.status_code == 400
    assert "invalid or expired" in resp.json()["detail"].lower()


def test_2fa_setup_blocked_when_not_allowed(
    client: TestClient, make_user: Callable[..., User], login: Callable[..., object]
) -> None:
    user = make_user("nokey", "Recruit123!")
    # Flip the per-account gate off directly.
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as db:
        row = db.get(User, user.id)
        row.can_enable_2fa = False
        db.commit()

    token = login(client, "nokey", "Recruit123!").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/api/v1/profile/2fa/setup", headers=headers)
    assert resp.status_code == 403
