# backend/tests/test_admin_2fa.py
from collections.abc import Callable

from fastapi.testclient import TestClient

import app.services.email as email
import app.services.otp as otp
from app.models import User


def test_admin_enable_forces_2fa_next_login(
    client: TestClient, auth_headers, make_user: Callable[..., User], login, monkeypatch
) -> None:
    monkeypatch.setattr(otp, "generate_code", lambda: "123456")
    monkeypatch.setattr(email, "send_email", lambda *a, **k: True)
    target = make_user("victim", "Recruit123!")

    resp = client.patch(
        f"/api/v1/admin/users/{target.id}",
        headers=auth_headers,
        json={"two_factor_enabled": True},
    )
    assert resp.status_code == 200
    assert resp.json()["two_factor_enabled"] is True
    assert resp.json()["two_factor_method"] == "email"

    # Next login now demands a code.
    body = login(client, "victim", "Recruit123!").json()
    assert body["two_factor_required"] is True


def test_admin_disable_clears_2fa(
    client: TestClient, auth_headers, make_user: Callable[..., User]
) -> None:
    target = make_user("hasit", two_factor_enabled=True, two_factor_method="email")
    resp = client.patch(
        f"/api/v1/admin/users/{target.id}",
        headers=auth_headers,
        json={"two_factor_enabled": False},
    )
    assert resp.status_code == 200
    assert resp.json()["two_factor_enabled"] is False
    assert resp.json()["two_factor_method"] is None


def test_admin_revoke_trusted_devices(
    client: TestClient, auth_headers, make_user: Callable[..., User]
) -> None:
    target = make_user("trusted", two_factor_enabled=True, two_factor_method="email")
    resp = client.post(
        f"/api/v1/admin/users/{target.id}/revoke-trusted-devices", headers=auth_headers
    )
    assert resp.status_code == 200
