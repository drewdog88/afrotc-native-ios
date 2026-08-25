# backend/tests/test_2fa_login.py
from collections.abc import Callable

from fastapi.testclient import TestClient

import app.services.email as email
import app.services.otp as otp
from app.models import User


def _fixed_code(monkeypatch, code: str = "123456") -> None:
    monkeypatch.setattr(otp, "generate_code", lambda: code)
    monkeypatch.setattr(email, "send_email", lambda *a, **k: True)


def _enrolled(make_user: Callable[..., User]) -> User:
    return make_user("mfa", "Recruit123!", two_factor_enabled=True, two_factor_method="email")


def test_login_with_2fa_returns_challenge_not_tokens(
    client: TestClient, make_user, login, monkeypatch
) -> None:
    _fixed_code(monkeypatch)
    _enrolled(make_user)
    resp = login(client, "mfa", "Recruit123!")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["two_factor_required"] is True
    assert body["method"] == "email"
    assert body["challenge_token"]
    assert body["access_token"] is None


def test_verify_issues_tokens(client: TestClient, make_user, login, monkeypatch) -> None:
    _fixed_code(monkeypatch)
    _enrolled(make_user)
    challenge = login(client, "mfa", "Recruit123!").json()["challenge_token"]
    resp = client.post(
        "/api/v1/auth/login/verify",
        json={"challenge_token": challenge, "code": "123456", "trust_device": False},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]


def test_wrong_code_is_401(client: TestClient, make_user, login, monkeypatch) -> None:
    _fixed_code(monkeypatch)
    _enrolled(make_user)
    challenge = login(client, "mfa", "Recruit123!").json()["challenge_token"]
    resp = client.post(
        "/api/v1/auth/login/verify",
        json={"challenge_token": challenge, "code": "999999", "trust_device": False},
    )
    assert resp.status_code == 401


def test_trust_device_then_skip_code(client: TestClient, make_user, login, monkeypatch) -> None:
    _fixed_code(monkeypatch)
    _enrolled(make_user)
    challenge = login(client, "mfa", "Recruit123!").json()["challenge_token"]
    verified = client.post(
        "/api/v1/auth/login/verify",
        json={"challenge_token": challenge, "code": "123456", "trust_device": True},
    )
    trust_token = verified.json()["trust_token"]
    assert trust_token
    # New login presenting the trust token skips the code and returns tokens.
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "mfa", "password": "Recruit123!", "trust_token": trust_token},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]
    assert resp.json().get("two_factor_required", False) is False


def test_no_2fa_login_still_returns_tokens(client: TestClient, make_user, login) -> None:
    make_user("plain", "Recruit123!")
    resp = login(client, "plain", "Recruit123!")
    assert resp.status_code == 200
    assert resp.json()["access_token"]
