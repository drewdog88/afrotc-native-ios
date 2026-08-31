"""Refresh token delivered as an httponly cookie (browser clients).

The refresh token is Secure, so exercise it over an https base_url — the default
http TestClient won't send a Secure cookie back (which is also why the existing
body-based refresh tests still pass: over http the cookie is absent and the
handler falls back to the request body, exactly the native-client path).
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.models import User

from .conftest import ADMIN_PASSWORD, ADMIN_USERNAME


def _https_client() -> TestClient:
    return TestClient(app, base_url="https://testserver")


def _login(client: TestClient):
    return client.post(
        "/api/v1/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )


def test_login_sets_httponly_refresh_cookie(admin_user: User) -> None:
    client = _https_client()
    resp = _login(client)
    assert resp.status_code == 200, resp.text
    # Access token still in the body (SPA reads it; iOS reads access + refresh).
    assert resp.json()["access_token"]
    set_cookie = resp.headers.get("set-cookie", "").lower()
    assert settings.refresh_cookie_name in set_cookie
    assert "httponly" in set_cookie
    assert "secure" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "path=/api/v1/auth" in set_cookie


def test_refresh_via_cookie_only(admin_user: User) -> None:
    client = _https_client()
    assert _login(client).status_code == 200
    # Empty body: the refresh token must be read from the httponly cookie.
    resp = client.post("/api/v1/auth/refresh", json={})
    assert resp.status_code == 200, resp.text
    new_access = resp.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me.status_code == 200


def test_refresh_without_cookie_or_body_is_401(admin_user: User) -> None:
    client = _https_client()  # never logged in → no cookie, no body token
    assert client.post("/api/v1/auth/refresh", json={}).status_code == 401


def test_logout_clears_cookie_and_blocks_refresh(admin_user: User) -> None:
    client = _https_client()
    access = _login(client).json()["access_token"]
    resp = client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {access}"}
    )
    assert resp.status_code == 204
    assert settings.refresh_cookie_name in resp.headers.get("set-cookie", "")
    # Session revoked + cookie cleared → a follow-up refresh must fail.
    assert client.post("/api/v1/auth/refresh", json={}).status_code == 401
