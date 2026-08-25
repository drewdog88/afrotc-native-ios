# backend/tests/test_2fa_password_revoke.py
from collections.abc import Callable

from fastapi.testclient import TestClient

import app.services.email as email
import app.services.otp as otp
from app.models import TrustedDevice, User
from tests.conftest import TestingSessionLocal


def _count_live_devices(user_id: int) -> int:
    with TestingSessionLocal() as db:
        return (
            db.query(TrustedDevice)
            .filter(TrustedDevice.user_id == user_id, TrustedDevice.revoked_at.is_(None))
            .count()
        )


def test_change_password_revokes_trusted_devices(
    client: TestClient, make_user: Callable[..., User], monkeypatch
) -> None:
    monkeypatch.setattr(otp, "generate_code", lambda: "123456")
    monkeypatch.setattr(email, "send_email", lambda *a, **k: True)
    user = make_user("pw", "OldPass123!", two_factor_enabled=True, two_factor_method="email")
    challenge = client.post(
        "/api/v1/auth/login", json={"username": "pw", "password": "OldPass123!"}
    ).json()["challenge_token"]
    tokens = client.post(
        "/api/v1/auth/login/verify",
        json={"challenge_token": challenge, "code": "123456", "trust_device": True},
    ).json()
    assert _count_live_devices(user.id) == 1

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    resp = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "OldPass123!", "new_password": "BrandNew123!"},
    )
    assert resp.status_code == 200
    assert _count_live_devices(user.id) == 0
