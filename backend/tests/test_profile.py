"""Profile self-service + the email 2FA enroll/verify/dismiss/disable lifecycle."""

from __future__ import annotations

from fastapi.testclient import TestClient

import app.services.email as email
import app.services.otp as otp


def _fixed(monkeypatch, code="123456"):
    monkeypatch.setattr(otp, "generate_code", lambda: code)
    monkeypatch.setattr(email, "send_email", lambda *a, **k: True)


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


def test_2fa_status_starts_disabled(client: TestClient, auth_headers) -> None:
    body = client.get("/api/v1/profile/2fa/status", headers=auth_headers).json()
    assert body["enabled"] is False
    assert body["method"] is None


def test_email_enroll_lifecycle(client: TestClient, auth_headers, monkeypatch) -> None:
    _fixed(monkeypatch)
    # Enroll sends a test code but does not activate.
    assert client.post(
        "/api/v1/profile/2fa/enroll", headers=auth_headers, json={"method": "email"}
    ).status_code == 200
    status = client.get("/api/v1/profile/2fa/status", headers=auth_headers).json()
    assert status["enabled"] is False
    # Verifying the code activates it.
    ok = client.post(
        "/api/v1/profile/2fa/enroll/verify", headers=auth_headers, json={"code": "123456"}
    )
    assert ok.status_code == 200
    status_body = client.get("/api/v1/profile/2fa/status", headers=auth_headers).json()
    assert status_body["enabled"] is True and status_body["method"] == "email"
    # Disable turns it off.
    assert client.post("/api/v1/profile/2fa/disable", headers=auth_headers).status_code == 200
    assert client.get("/api/v1/profile/2fa/status", headers=auth_headers).json()["enabled"] is False


def test_enroll_verify_wrong_code_is_400(client: TestClient, auth_headers, monkeypatch) -> None:
    _fixed(monkeypatch)
    client.post("/api/v1/profile/2fa/enroll", headers=auth_headers, json={"method": "email"})
    resp = client.post(
        "/api/v1/profile/2fa/enroll/verify", headers=auth_headers, json={"code": "000000"}
    )
    assert resp.status_code == 400


def test_enrollment_dismiss_sets_flag(client: TestClient, auth_headers) -> None:
    dismiss = client.post("/api/v1/profile/2fa/enrollment-dismiss", headers=auth_headers)
    assert dismiss.status_code == 200
    status = client.get("/api/v1/profile/2fa/status", headers=auth_headers).json()
    assert status["enrollment_prompted"] is True


def test_enroll_rejects_unknown_method(client: TestClient, auth_headers) -> None:
    resp = client.post("/api/v1/profile/2fa/enroll", headers=auth_headers, json={"method": "sms"})
    assert resp.status_code == 400
