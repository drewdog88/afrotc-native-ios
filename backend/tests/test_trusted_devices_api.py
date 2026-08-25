from fastapi.testclient import TestClient

import app.services.email as email
import app.services.otp as otp


def _fixed(monkeypatch, code="123456"):
    monkeypatch.setattr(otp, "generate_code", lambda: code)
    monkeypatch.setattr(email, "send_email", lambda *a, **k: True)


def _login_2fa_with_trust(client, username, password):
    challenge = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    ).json()["challenge_token"]
    return client.post(
        "/api/v1/auth/login/verify",
        json={"challenge_token": challenge, "code": "123456", "trust_device": True},
    ).json()


def test_list_and_revoke_trusted_devices(client: TestClient, make_user, monkeypatch) -> None:
    _fixed(monkeypatch)
    make_user("dv", "Recruit123!", two_factor_enabled=True, two_factor_method="email")
    tokens = _login_2fa_with_trust(client, "dv", "Recruit123!")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    devices = client.get("/api/v1/profile/trusted-devices", headers=headers).json()
    assert len(devices) == 1
    device_id = devices[0]["id"]

    assert (
        client.delete(f"/api/v1/profile/trusted-devices/{device_id}", headers=headers).status_code
        == 200
    )
    assert client.get("/api/v1/profile/trusted-devices", headers=headers).json() == []
