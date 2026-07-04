"""Export endpoints: CSV/XLSX/PDF downloads for each entity, plus validation."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _seed_one_of_each(client: TestClient, headers: dict[str, str]) -> None:
    client.post(
        "/api/v1/recruits",
        headers=headers,
        json={
            "first_name": "Jordan",
            "last_name": "Rivers",
            "email": "jordan.rivers@example.com",
            "current_school": "Ballard High School",
            "school_type": "high_school",
        },
    )
    client.post(
        "/api/v1/cadets",
        headers=headers,
        json={
            "first_name": "Dakota",
            "last_name": "Fields",
            "email": "dakota.fields@example.com",
            "major": "Aeronautics",
            "graduation_year": 2027,
            "cadet_rank": "C/2d Lt",
        },
    )
    client.post(
        "/api/v1/contacts",
        headers=headers,
        json={
            "university_name": "University of Washington",
            "contact_name": "Col. Pat Emerson",
            "email": "pat.emerson@example.com",
        },
    )
    client.post(
        "/api/v1/events",
        headers=headers,
        json={
            "title": "UW STEM College Fair",
            "event_date": "2026-10-15",
            "event_type": "college_fair",
        },
    )


def test_export_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/export/recruits", params={"format": "csv"}).status_code == 401


def test_csv_export_has_data_and_headers(client: TestClient, auth_headers: dict[str, str]) -> None:
    _seed_one_of_each(client, auth_headers)
    resp = client.get("/api/v1/export/recruits", headers=auth_headers, params={"format": "csv"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=recruits.csv" in resp.headers["content-disposition"]
    body = resp.text
    assert "First Name" in body
    assert "Jordan" in body and "Rivers" in body


def test_every_entity_and_format_streams(client: TestClient, auth_headers: dict[str, str]) -> None:
    _seed_one_of_each(client, auth_headers)
    media = {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf",
    }
    for entity in ("recruits", "cadets", "contacts", "events"):
        for fmt, mime in media.items():
            resp = client.get(
                f"/api/v1/export/{entity}", headers=auth_headers, params={"format": fmt}
            )
            assert resp.status_code == 200, f"{entity}/{fmt}: {resp.status_code}"
            assert resp.headers["content-type"].startswith(mime), f"{entity}/{fmt}"
            assert len(resp.content) > 0, f"{entity}/{fmt} was empty"


def test_export_on_empty_table_still_succeeds(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    # No rows seeded — the export should be a valid (header-only) CSV, not a 500.
    resp = client.get("/api/v1/export/cadets", headers=auth_headers, params={"format": "csv"})
    assert resp.status_code == 200


def test_unknown_entity_is_422(client: TestClient, auth_headers: dict[str, str]) -> None:
    # `entity` is a Literal path param, so FastAPI rejects unknown values at validation.
    resp = client.get("/api/v1/export/widgets", headers=auth_headers, params={"format": "csv"})
    assert resp.status_code == 422


def test_unknown_format_is_422(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/export/recruits", headers=auth_headers, params={"format": "yaml"})
    assert resp.status_code == 422
