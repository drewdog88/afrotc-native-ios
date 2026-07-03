"""Recruits: CRUD, the append-only stage funnel, and auth gating."""
from __future__ import annotations

from fastapi.testclient import TestClient

_NEW_RECRUIT = {
    "first_name": "Jordan",
    "last_name": "Rivers",
    "email": "jordan.rivers@example.com",
    "current_school": "Ballard High School",
    "school_type": "high_school",
}


def _create(client: TestClient, headers: dict[str, str], **overrides) -> dict:
    body = {**_NEW_RECRUIT, **overrides}
    resp = client.post("/api/v1/recruits", headers=headers, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_recruits_require_auth(client: TestClient) -> None:
    assert client.get("/api/v1/recruits").status_code == 401


def test_create_seeds_a_baseline_stage_event(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    recruit = _create(client, auth_headers)
    assert recruit["stage"] == "lead"  # default stage
    assert recruit["full_name"] == "Jordan Rivers"

    history = client.get(
        f"/api/v1/recruits/{recruit['id']}/stage-history", headers=auth_headers
    ).json()
    assert len(history) == 1
    assert history[0]["from_stage"] is None
    assert history[0]["to_stage"] == "lead"


def test_get_and_list(client: TestClient, auth_headers: dict[str, str]) -> None:
    recruit = _create(client, auth_headers)
    got = client.get(f"/api/v1/recruits/{recruit['id']}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["id"] == recruit["id"]

    listing = client.get("/api/v1/recruits", headers=auth_headers).json()
    assert listing["total"] == 1
    assert listing["items"][0]["id"] == recruit["id"]


def test_search_filters_the_list(client: TestClient, auth_headers: dict[str, str]) -> None:
    _create(client, auth_headers, first_name="Alex", last_name="Stone")
    _create(client, auth_headers, first_name="Blair", last_name="Winters")

    resp = client.get("/api/v1/recruits", headers=auth_headers, params={"search": "Winters"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["last_name"] == "Winters"


def test_stage_change_appends_event(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    recruit = _create(client, auth_headers)
    resp = client.post(
        f"/api/v1/recruits/{recruit['id']}/stage",
        headers=auth_headers,
        json={"to_stage": "contacted", "note": "Reached out at the college fair"},
    )
    assert resp.status_code == 200
    assert resp.json()["stage"] == "contacted"

    history = client.get(
        f"/api/v1/recruits/{recruit['id']}/stage-history", headers=auth_headers
    ).json()
    assert [e["to_stage"] for e in history] == ["lead", "contacted"]


def test_stage_change_to_same_stage_is_rejected(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    recruit = _create(client, auth_headers)
    resp = client.post(
        f"/api/v1/recruits/{recruit['id']}/stage",
        headers=auth_headers,
        json={"to_stage": "lead"},
    )
    assert resp.status_code == 400


def test_update_and_delete(client: TestClient, auth_headers: dict[str, str]) -> None:
    recruit = _create(client, auth_headers)

    patched = client.patch(
        f"/api/v1/recruits/{recruit['id']}",
        headers=auth_headers,
        json={"notes": "Strong STEM candidate"},
    )
    assert patched.status_code == 200
    assert patched.json()["notes"] == "Strong STEM candidate"

    assert (
        client.delete(f"/api/v1/recruits/{recruit['id']}", headers=auth_headers).status_code
        == 204
    )
    assert client.get(f"/api/v1/recruits/{recruit['id']}", headers=auth_headers).status_code == 404
