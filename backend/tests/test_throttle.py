"""Per-IP throttle on the unauthenticated auth endpoints (issue #18 / #4)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


def test_login_is_throttled_per_ip(
    client: TestClient, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "auth_rate_limit_max", 3)
    make_user("target")
    # The first `max` attempts pass the throttle (rejected on bad creds, 401);
    # the next one is refused by the throttle itself with 429.
    for _ in range(3):
        r = client.post("/api/v1/auth/login", json={"username": "target", "password": "nope"})
        assert r.status_code == 401, r.text
    blocked = client.post("/api/v1/auth/login", json={"username": "target", "password": "nope"})
    assert blocked.status_code == 429


def test_forgot_password_is_throttled_per_ip(
    client: TestClient, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "auth_rate_limit_max", 2)
    make_user("recover")
    for _ in range(2):
        r = client.post("/api/v1/auth/forgot-password", json={"username": "recover"})
        assert r.status_code == 200, r.text
    blocked = client.post("/api/v1/auth/forgot-password", json={"username": "recover"})
    assert blocked.status_code == 429


def test_throttle_is_keyed_per_endpoint(
    client: TestClient, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Exhausting the login bucket must not spill over onto forgot-password.
    monkeypatch.setattr(settings, "auth_rate_limit_max", 2)
    make_user("split")
    for _ in range(3):
        client.post("/api/v1/auth/login", json={"username": "split", "password": "nope"})
    # login is now blocked...
    assert client.post(
        "/api/v1/auth/login", json={"username": "split", "password": "nope"}
    ).status_code == 429
    # ...but forgot-password has its own independent bucket.
    assert client.post(
        "/api/v1/auth/forgot-password", json={"username": "split"}
    ).status_code == 200
