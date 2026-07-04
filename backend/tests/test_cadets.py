"""Cadets: CRUD, search/filter, and auth gating."""

from __future__ import annotations

from fastapi.testclient import TestClient

_NEW_CADET = {
    "first_name": "Dakota",
    "last_name": "Fields",
    "email": "dakota.fields@example.com",
    "major": "Aeronautics",
    "graduation_year": 2027,
    "cadet_rank": "C/2d Lt",
    "hometown": "Spokane, WA",
}


def _create(client: TestClient, headers: dict[str, str], **overrides) -> dict:
    body = {**_NEW_CADET, **overrides}
    resp = client.post("/api/v1/cadets", headers=headers, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_cadets_require_auth(client: TestClient) -> None:
    assert client.get("/api/v1/cadets").status_code == 401


def test_create_defaults_to_active(client: TestClient, auth_headers: dict[str, str]) -> None:
    cadet = _create(client, auth_headers)
    assert cadet["status"] == "active"
    assert cadet["full_name"] == "Dakota Fields"


def test_get_and_list(client: TestClient, auth_headers: dict[str, str]) -> None:
    cadet = _create(client, auth_headers)
    got = client.get(f"/api/v1/cadets/{cadet['id']}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["id"] == cadet["id"]

    listing = client.get("/api/v1/cadets", headers=auth_headers).json()
    assert listing["total"] == 1
    assert listing["items"][0]["id"] == cadet["id"]


def test_get_missing_is_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert client.get("/api/v1/cadets/999", headers=auth_headers).status_code == 404


def test_search_and_status_filter(client: TestClient, auth_headers: dict[str, str]) -> None:
    _create(client, auth_headers, first_name="Riley", last_name="Cascade", major="Physics")
    _create(
        client,
        auth_headers,
        first_name="Morgan",
        last_name="Rainier",
        email="morgan.rainier@example.com",
        status="graduated",
    )

    by_name = client.get(
        "/api/v1/cadets", headers=auth_headers, params={"search": "Cascade"}
    ).json()
    assert by_name["total"] == 1
    assert by_name["items"][0]["last_name"] == "Cascade"

    graduated = client.get(
        "/api/v1/cadets", headers=auth_headers, params={"status": "graduated"}
    ).json()
    assert graduated["total"] == 1
    assert graduated["items"][0]["status"] == "graduated"


def test_update_and_delete(client: TestClient, auth_headers: dict[str, str]) -> None:
    cadet = _create(client, auth_headers)

    patched = client.patch(
        f"/api/v1/cadets/{cadet['id']}",
        headers=auth_headers,
        json={"status": "inactive", "unenrollment_reason": "Transferred"},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "inactive"
    assert patched.json()["unenrollment_reason"] == "Transferred"

    assert client.delete(f"/api/v1/cadets/{cadet['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/v1/cadets/{cadet['id']}", headers=auth_headers).status_code == 404
