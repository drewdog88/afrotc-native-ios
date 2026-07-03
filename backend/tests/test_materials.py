"""Materials: document upload/download (bytea round-trip) and the size guard."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


def test_upload_then_download_round_trips_bytes(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    payload = b"Det 695 recruiting one-pager\n%PDF-fake-bytes"
    resp = client.post(
        "/api/v1/materials/documents",
        headers=auth_headers,
        params={"title": "Recruiting One-Pager", "category": "flyers"},
        files={"file": ("onepager.pdf", payload, "application/pdf")},
    )
    assert resp.status_code == 201, resp.text
    doc = resp.json()
    assert doc["title"] == "Recruiting One-Pager"
    assert doc["file_size"] == len(payload)
    assert doc["original_filename"] == "onepager.pdf"

    dl = client.get(f"/api/v1/materials/documents/{doc['id']}/download", headers=auth_headers)
    assert dl.status_code == 200
    assert dl.content == payload
    assert "onepager.pdf" in dl.headers["content-disposition"]


def test_upload_over_the_limit_is_413(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "max_upload_bytes", 8)
    resp = client.post(
        "/api/v1/materials/documents",
        headers=auth_headers,
        files={"file": ("big.bin", b"way past eight bytes", "application/octet-stream")},
    )
    assert resp.status_code == 413


def test_download_missing_document_is_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.get("/api/v1/materials/documents/999/download", headers=auth_headers)
    assert resp.status_code == 404


def test_document_upload_requires_auth(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/materials/documents",
        files={"file": ("x.txt", b"hi", "text/plain")},
    )
    assert resp.status_code == 401


def test_links_crud(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = client.post(
        "/api/v1/materials/links",
        headers=auth_headers,
        json={"title": "AFROTC Home", "url": "https://www.afrotc.com", "category": "official"},
    )
    assert created.status_code == 201, created.text
    link_id = created.json()["id"]

    listing = client.get("/api/v1/materials/links", headers=auth_headers).json()
    assert listing["total"] == 1

    assert (
        client.delete(f"/api/v1/materials/links/{link_id}", headers=auth_headers).status_code
        == 204
    )
