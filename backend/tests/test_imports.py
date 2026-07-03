"""Bulk import: per-row validation and unsupported-format handling."""
from __future__ import annotations

from fastapi.testclient import TestClient

# Row 1 is valid; row 2 omits the required `current_school`.
_CSV = (
    "first_name,last_name,current_school,school_type\n"
    "Riley,Summit,Garfield High School,high_school\n"
    "Casey,Valley,,high_school\n"
)


def test_import_reports_per_row_errors(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/api/v1/recruits/import",
        headers=auth_headers,
        files={"file": ("recruits.csv", _CSV.encode(), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_rows"] == 2
    assert body["imported"] == 1
    assert body["failed"] == 1
    assert body["errors"][0]["row"] == 2
    assert any("current_school" in msg for msg in body["errors"][0]["errors"])

    # The one valid row actually landed.
    listing = client.get("/api/v1/recruits", headers=auth_headers).json()
    assert listing["total"] == 1
    assert listing["items"][0]["last_name"] == "Summit"


def test_import_rejects_unsupported_format(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/api/v1/recruits/import",
        headers=auth_headers,
        files={"file": ("notes.txt", b"not a spreadsheet", "text/plain")},
    )
    assert resp.status_code == 400


def test_import_requires_auth(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/recruits/import",
        files={"file": ("recruits.csv", _CSV.encode(), "text/csv")},
    )
    assert resp.status_code == 401
