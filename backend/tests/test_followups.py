"""Follow-ups: CRUD, the assignee/status/due filters, and the complete action."""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models import User

_NEW_FOLLOWUP = {
    "note": "Call the UW cadre about the fall fair",
    "due_date": "2026-09-01T17:00:00",
}


def _create(client: TestClient, headers: dict[str, str], **overrides) -> dict:
    body = {**_NEW_FOLLOWUP, **overrides}
    resp = client.post("/api/v1/followups", headers=headers, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_followups_require_auth(client: TestClient) -> None:
    assert client.get("/api/v1/followups").status_code == 401


def test_create_records_the_author_and_defaults_open(
    client: TestClient, auth_headers: dict[str, str], admin_user: User
) -> None:
    followup = _create(client, auth_headers)
    assert followup["status"] == "open"
    assert followup["completed_at"] is None
    # create_followup stamps the acting user as author.
    assert followup["created_by_id"] == admin_user.id


def test_get_and_list(client: TestClient, auth_headers: dict[str, str]) -> None:
    followup = _create(client, auth_headers)
    got = client.get(f"/api/v1/followups/{followup['id']}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["id"] == followup["id"]

    listing = client.get("/api/v1/followups", headers=auth_headers).json()
    assert listing["total"] == 1


def test_get_missing_is_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert client.get("/api/v1/followups/999", headers=auth_headers).status_code == 404


def test_assignee_me_filter(
    client: TestClient, auth_headers: dict[str, str], admin_user: User
) -> None:
    _create(client, auth_headers, assignee_id=admin_user.id)
    _create(client, auth_headers, note="Unassigned task")  # assignee_id None

    mine = client.get(
        "/api/v1/followups", headers=auth_headers, params={"assignee_id": "me"}
    ).json()
    assert mine["total"] == 1
    assert mine["items"][0]["assignee_id"] == admin_user.id


def test_bad_assignee_id_is_400(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/followups", headers=auth_headers, params={"assignee_id": "nobody"})
    assert resp.status_code == 400


def test_status_and_due_before_filters(client: TestClient, auth_headers: dict[str, str]) -> None:
    early = _create(client, auth_headers, due_date="2026-01-15T12:00:00")
    _create(client, auth_headers, due_date="2026-12-15T12:00:00")

    due_q1 = client.get(
        "/api/v1/followups", headers=auth_headers, params={"due_before": "2026-06-01"}
    ).json()
    assert due_q1["total"] == 1
    assert due_q1["items"][0]["id"] == early["id"]

    open_only = client.get(
        "/api/v1/followups", headers=auth_headers, params={"status": "open"}
    ).json()
    assert open_only["total"] == 2


def test_complete_marks_done_and_stamps_time(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    followup = _create(client, auth_headers)
    resp = client.post(f"/api/v1/followups/{followup['id']}/complete", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "done"
    assert body["completed_at"] is not None


def test_completing_twice_is_400(client: TestClient, auth_headers: dict[str, str]) -> None:
    followup = _create(client, auth_headers)
    assert (
        client.post(
            f"/api/v1/followups/{followup['id']}/complete", headers=auth_headers
        ).status_code
        == 200
    )
    again = client.post(f"/api/v1/followups/{followup['id']}/complete", headers=auth_headers)
    assert again.status_code == 400
    assert "already completed" in again.json()["detail"].lower()


def test_update_and_delete(client: TestClient, auth_headers: dict[str, str]) -> None:
    followup = _create(client, auth_headers)

    patched = client.patch(
        f"/api/v1/followups/{followup['id']}",
        headers=auth_headers,
        json={"note": "Rescheduled — email instead", "due_date": "2026-10-01T09:00:00"},
    )
    assert patched.status_code == 200
    assert patched.json()["note"] == "Rescheduled — email instead"
    assert patched.json()["due_date"].startswith("2026-10-01")

    assert (
        client.delete(f"/api/v1/followups/{followup['id']}", headers=auth_headers).status_code
        == 204
    )
    assert (
        client.get(f"/api/v1/followups/{followup['id']}", headers=auth_headers).status_code == 404
    )


def test_complete_requires_write(
    client: TestClient, make_user: Callable[..., User], login: Callable[..., object]
) -> None:
    from app.models.enums import UserRole

    make_user("viewer_fu", "Viewer123!", role=UserRole.VIEWER)
    token = login(client, "viewer_fu", "Viewer123!").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # require_write runs before the handler, so this 403s even for a missing id.
    assert client.post("/api/v1/followups/1/complete", headers=headers).status_code == 403
