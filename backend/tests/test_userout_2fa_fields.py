from fastapi.testclient import TestClient


def test_me_exposes_2fa_enrollment_fields(client: TestClient, auth_headers) -> None:
    body = client.get("/api/v1/auth/me", headers=auth_headers).json()
    assert body["two_factor_enabled"] is False
    assert body["two_factor_method"] is None
    assert body["two_factor_enrollment_prompted"] is False
