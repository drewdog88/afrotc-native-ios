"""Analytics: the funnel counts every stage and the dashboard totals add up."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.enums import FUNNEL_ORDER


def _seed_recruit(client: TestClient, headers: dict[str, str], last_name: str, stage: str) -> None:
    resp = client.post(
        "/api/v1/recruits",
        headers=headers,
        json={
            "first_name": "Pat",
            "last_name": last_name,
            "current_school": "University of Washington",
            "school_type": "college",
            "stage": stage,
        },
    )
    assert resp.status_code == 201, resp.text


def test_funnel_includes_every_stage(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _seed_recruit(client, auth_headers, "Lead", "lead")
    _seed_recruit(client, auth_headers, "Alsolead", "lead")
    _seed_recruit(client, auth_headers, "Applied", "applied")

    resp = client.get("/api/v1/analytics/funnel", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()

    counts = {s["stage"]: s["count"] for s in body["stages"]}
    # Every funnel stage is reported, even the empty ones.
    for stage in FUNNEL_ORDER:
        assert stage.value in counts
    assert counts["lead"] == 2
    assert counts["applied"] == 1
    assert body["total"] == 3


def test_dashboard_stats_totals(client: TestClient, auth_headers: dict[str, str]) -> None:
    _seed_recruit(client, auth_headers, "One", "lead")
    _seed_recruit(client, auth_headers, "Two", "contacted")

    resp = client.get("/api/v1/dashboard/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_recruits"] == 2
    assert body["open_followups"] == 0
    # recruits_by_stage always carries the full funnel ladder.
    stages = {s["stage"] for s in body["recruits_by_stage"]}
    assert {stage.value for stage in FUNNEL_ORDER}.issubset(stages)
