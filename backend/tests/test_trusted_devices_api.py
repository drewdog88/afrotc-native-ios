from fastapi.testclient import TestClient

import app.services.email as email
import app.services.otp as otp
from app.core.config import settings


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


def test_revoke_others_keeps_current_device(client: TestClient, make_user, monkeypatch) -> None:
    """revoke-others should drop the OTHER trusted device but keep the CURRENT one."""
    _fixed(monkeypatch)
    make_user("dv2", "Recruit123!", two_factor_enabled=True, two_factor_method="email")

    # Two trusted logins -> two devices. Grab the raw trust token for the second
    # login's device (returned directly in the verify response body) and send it
    # explicitly as the trust cookie on the revoke-others call, since the
    # TestClient's cookie jar normalizes the "testserver" host and won't round-trip
    # a Secure cookie set by the app on its own.
    _login_2fa_with_trust(client, "dv2", "Recruit123!")
    tokens2 = _login_2fa_with_trust(client, "dv2", "Recruit123!")
    headers = {"Authorization": f"Bearer {tokens2['access_token']}"}
    current_trust_token = tokens2["trust_token"]
    assert current_trust_token

    devices_before = client.get("/api/v1/profile/trusted-devices", headers=headers).json()
    assert len(devices_before) == 2
    # list_devices orders by last_used_at desc, so the most recently created
    # (second) login's device is first — that's the "current" device.
    current_device_id = devices_before[0]["id"]

    client.cookies.set(settings.trusted_device_cookie_name, current_trust_token)
    resp = client.post("/api/v1/profile/trusted-devices/revoke-others", headers=headers)
    assert resp.status_code == 200, resp.text

    devices_after = client.get("/api/v1/profile/trusted-devices", headers=headers).json()
    assert len(devices_after) == 1
    assert devices_after[0]["id"] == current_device_id


def test_revoke_others_preserves_current_device_via_body_token(
    client: TestClient, make_user, monkeypatch
) -> None:
    _fixed(monkeypatch)
    make_user("dvbody", "Recruit123!", two_factor_enabled=True, two_factor_method="email")
    # First trusted login → device A (this is the "current" device / token).
    tokens_a = _login_2fa_with_trust(client, "dvbody", "Recruit123!")
    current = tokens_a["trust_token"]
    headers = {"Authorization": f"Bearer {tokens_a['access_token']}"}
    # Second trusted login → device B.
    _login_2fa_with_trust(client, "dvbody", "Recruit123!")
    assert len(client.get("/api/v1/profile/trusted-devices", headers=headers).json()) == 2

    # Revoke others, presenting device A's token in the BODY (no cookie reliance).
    resp = client.post(
        "/api/v1/profile/trusted-devices/revoke-others",
        headers=headers,
        json={"trust_token": current},
    )
    assert resp.status_code == 200
    remaining = client.get("/api/v1/profile/trusted-devices", headers=headers).json()
    assert len(remaining) == 1  # device A survived
