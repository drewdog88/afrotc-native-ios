"""University/high-school contacts: CRUD, search, active filter, auth gating."""

from __future__ import annotations

from fastapi.testclient import TestClient

_NEW_CONTACT = {
    "university_name": "University of Washington",
    "contact_name": "Col. Pat Emerson",
    "contact_title": "Recruiting Liaison",
    "email": "pat.emerson@example.com",
    "address": "Seattle, WA",
    "latitude": 47.6553,
    "longitude": -122.3035,
}


def _create(client: TestClient, headers: dict[str, str], **overrides) -> dict:
    body = {**_NEW_CONTACT, **overrides}
    resp = client.post("/api/v1/contacts", headers=headers, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_contacts_require_auth(client: TestClient) -> None:
    assert client.get("/api/v1/contacts").status_code == 401


def test_create_defaults_to_active_and_keeps_coords(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    contact = _create(client, auth_headers)
    assert contact["is_active"] is True
    assert contact["latitude"] == 47.6553
    assert contact["longitude"] == -122.3035


def test_get_and_list(client: TestClient, auth_headers: dict[str, str]) -> None:
    contact = _create(client, auth_headers)
    got = client.get(f"/api/v1/contacts/{contact['id']}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["university_name"] == "University of Washington"

    listing = client.get("/api/v1/contacts", headers=auth_headers).json()
    assert listing["total"] == 1


def test_get_missing_is_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert client.get("/api/v1/contacts/999", headers=auth_headers).status_code == 404


def test_search_and_active_filter(client: TestClient, auth_headers: dict[str, str]) -> None:
    _create(
        client,
        auth_headers,
        university_name="Oregon State University",
        contact_name="Maj. Dana Willamette",
        email="dana.willamette@example.com",
    )
    _create(
        client,
        auth_headers,
        university_name="Gonzaga University",
        contact_name="Capt. Lee Spokane",
        email="lee.spokane@example.com",
        is_active=False,
    )

    by_name = client.get(
        "/api/v1/contacts", headers=auth_headers, params={"search": "Oregon State"}
    ).json()
    assert by_name["total"] == 1
    assert by_name["items"][0]["university_name"] == "Oregon State University"

    inactive = client.get(
        "/api/v1/contacts", headers=auth_headers, params={"is_active": "false"}
    ).json()
    assert inactive["total"] == 1
    assert inactive["items"][0]["is_active"] is False


def test_update_and_delete(client: TestClient, auth_headers: dict[str, str]) -> None:
    contact = _create(client, auth_headers)

    patched = client.patch(
        f"/api/v1/contacts/{contact['id']}",
        headers=auth_headers,
        json={"is_active": False, "notes": "On sabbatical"},
    )
    assert patched.status_code == 200
    assert patched.json()["is_active"] is False
    assert patched.json()["notes"] == "On sabbatical"

    assert (
        client.delete(f"/api/v1/contacts/{contact['id']}", headers=auth_headers).status_code == 204
    )
    assert client.get(f"/api/v1/contacts/{contact['id']}", headers=auth_headers).status_code == 404
