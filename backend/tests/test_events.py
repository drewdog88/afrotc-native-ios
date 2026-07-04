"""Recruitment events: CRUD, search/filter, default status, auth gating."""

from __future__ import annotations

from fastapi.testclient import TestClient

_NEW_EVENT = {
    "title": "UW STEM College Fair",
    "event_date": "2026-10-15",
    "event_type": "college_fair",
    "location": "University of Washington, Seattle, WA",
    "start_time": "09:00:00",
    "end_time": "15:00:00",
}


def _create(client: TestClient, headers: dict[str, str], **overrides) -> dict:
    body = {**_NEW_EVENT, **overrides}
    resp = client.post("/api/v1/events", headers=headers, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_events_require_auth(client: TestClient) -> None:
    assert client.get("/api/v1/events").status_code == 401


def test_create_defaults_to_scheduled(client: TestClient, auth_headers: dict[str, str]) -> None:
    event = _create(client, auth_headers)
    assert event["status"] == "scheduled"
    assert event["attendees_count"] == 0
    assert event["title"] == "UW STEM College Fair"


def test_get_and_list(client: TestClient, auth_headers: dict[str, str]) -> None:
    event = _create(client, auth_headers)
    got = client.get(f"/api/v1/events/{event['id']}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["id"] == event["id"]

    listing = client.get("/api/v1/events", headers=auth_headers).json()
    assert listing["total"] == 1


def test_get_missing_is_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert client.get("/api/v1/events/999", headers=auth_headers).status_code == 404


def test_search_and_type_filter(client: TestClient, auth_headers: dict[str, str]) -> None:
    _create(
        client,
        auth_headers,
        title="Gonzaga Campus Visit",
        event_type="school_visit",
        location="Gonzaga University, Spokane, WA",
    )
    _create(
        client,
        auth_headers,
        title="Oregon State Info Session",
        event_type="info_session",
        location="Corvallis, OR",
    )

    by_title = client.get(
        "/api/v1/events", headers=auth_headers, params={"search": "Gonzaga"}
    ).json()
    assert by_title["total"] == 1
    assert by_title["items"][0]["title"] == "Gonzaga Campus Visit"

    by_type = client.get(
        "/api/v1/events", headers=auth_headers, params={"event_type": "info_session"}
    ).json()
    assert by_type["total"] == 1
    assert by_type["items"][0]["event_type"] == "info_session"


def test_update_and_delete(client: TestClient, auth_headers: dict[str, str]) -> None:
    event = _create(client, auth_headers)

    patched = client.patch(
        f"/api/v1/events/{event['id']}",
        headers=auth_headers,
        json={"status": "completed", "attendees_count": 42},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "completed"
    assert patched.json()["attendees_count"] == 42

    assert client.delete(f"/api/v1/events/{event['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/v1/events/{event['id']}", headers=auth_headers).status_code == 404
